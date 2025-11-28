"""Log chunking utilities for managing context windows and token limits."""

import math
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

from ..utils.logger import setup_logger
from ..utils.config import config

logger = setup_logger()


class LogChunk:
    """
    Represents a chunk of log entries with metadata.
    """
    
    def __init__(
        self,
        logs: pd.DataFrame,
        chunk_id: int,
        start_index: int,
        end_index: int,
        focus_entity: Optional[str] = None
    ):
        """
        Initialize a log chunk.
        
        Args:
            logs: DataFrame containing log entries
            chunk_id: Unique identifier for this chunk
            start_index: Starting index in original log file
            end_index: Ending index in original log file
            focus_entity: Optional entity this chunk focuses on
        """
        self.logs = logs
        self.chunk_id = chunk_id
        self.start_index = start_index
        self.end_index = end_index
        self.focus_entity = focus_entity
        self.token_estimate = self._estimate_tokens()
    
    def _estimate_tokens(self) -> int:
        """
        Estimate token count for this chunk.
        Rough estimate: ~4 characters per token.
        """
        try:
            # Convert entire dataframe to string and count characters
            total_chars = len(self.logs.to_string())
            return int(total_chars / 4)
        except Exception as e:
            # Fallback: rough estimate
            return len(self.logs) * 50  # Assume ~50 tokens per log entry
    
    def to_text(self, include_headers: bool = True) -> str:
        """
        Convert chunk to text representation for LLM.
        
        Args:
            include_headers: Whether to include column headers
            
        Returns:
            Text representation of the chunk
        """
        if include_headers:
            return self.logs.to_string(index=False)
        else:
            return self.logs.to_string(index=False, header=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert chunk to dictionary representation.
        
        Returns:
            Dictionary with chunk metadata and data
        """
        return {
            "chunk_id": self.chunk_id,
            "start_index": self.start_index,
            "end_index": self.end_index,
            "focus_entity": self.focus_entity,
            "token_estimate": self.token_estimate,
            "entry_count": len(self.logs),
            "logs": self.logs.to_dict(orient='records')
        }
    
    def __len__(self) -> int:
        """Return number of log entries in this chunk."""
        return len(self.logs)
    
    def __repr__(self) -> str:
        return (
            f"LogChunk(id={self.chunk_id}, "
            f"entries={len(self.logs)}, "
            f"tokens≈{self.token_estimate}, "
            f"entity={self.focus_entity})"
        )


class LogChunker:
    """
    Handles chunking of log data for LLM processing.
    
    Features:
    - Size-based chunking with token limits
    - Entity-context based chunking
    - Overlapping chunks for context preservation
    - Smart chunk merging
    """
    
    def __init__(self):
        """Initialize chunker with configuration."""
        self.chunking_config = config.get_chunking_config()
        self.max_tokens = self.chunking_config.get('max_tokens', 4000)
        self.overlap_lines = self.chunking_config.get('overlap_lines', 10)
        self.context_lines = self.chunking_config.get('context_lines', 50)
        
        logger.info(f"Initialized LogChunker (max_tokens={self.max_tokens})")
    
    def chunk_by_size(
        self,
        logs: pd.DataFrame,
        max_tokens: Optional[int] = None
    ) -> List[LogChunk]:
        """
        Chunk logs by size with token limit.
        
        Args:
            logs: DataFrame of log entries
            max_tokens: Maximum tokens per chunk (default: from config)
            
        Returns:
            List of LogChunk objects
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
        
        if len(logs) == 0:
            return []
        
        chunks = []
        chunk_id = 0
        current_start = 0
        
        # Estimate average tokens per log entry
        sample_size = min(10, len(logs))
        sample_text = logs.head(sample_size).to_string()
        avg_tokens_per_entry = (len(sample_text) / 4) / sample_size
        
        # Calculate entries per chunk
        entries_per_chunk = max(1, int(max_tokens / avg_tokens_per_entry))
        
        logger.info(
            f"Chunking {len(logs)} entries: "
            f"~{avg_tokens_per_entry:.1f} tokens/entry, "
            f"~{entries_per_chunk} entries/chunk, "
            f"overlap_lines={self.overlap_lines}"
        )
        
        loop_count = 0
        max_loops = len(logs) * 2  # Safety limit
        while current_start < len(logs):
            loop_count += 1
            if loop_count > max_loops:
                logger.error(f"Infinite loop detected in chunk_by_size! Breaking after {loop_count} iterations")
                break
            
            logger.debug(f"Loop {loop_count}: current_start={current_start}, len(logs)={len(logs)}")
            current_end = min(current_start + entries_per_chunk, len(logs))
            
            logger.debug(f"  Slicing logs from {current_start} to {current_end}")
            chunk_logs = logs.iloc[current_start:current_end]
            
            logger.debug(f"  Creating LogChunk object...")
            chunk = LogChunk(
                logs=chunk_logs,
                chunk_id=chunk_id,
                start_index=current_start,
                end_index=current_end
            )
            logger.debug(f"  LogChunk created successfully")
            
            chunks.append(chunk)
            
            # If we've reached the end, we're done
            if current_end >= len(logs):
                break
            
            # Move forward with overlap
            # Ensure we make forward progress even with overlap
            next_start = current_end - self.overlap_lines
            if next_start <= current_start:
                # If overlap would prevent progress, just move forward by at least 1
                next_start = current_start + max(1, entries_per_chunk // 2)
            
            current_start = next_start
            chunk_id += 1
        
        logger.info(f"Created {len(chunks)} size-based chunks")
        return chunks
    
    def chunk_by_entity_context(
        self,
        logs: pd.DataFrame,
        entity_indices: List[int],
        entity_name: str,
        context_lines: Optional[int] = None
    ) -> List[LogChunk]:
        """
        Create chunks centered around entity occurrences.
        
        Args:
            logs: DataFrame of log entries
            entity_indices: Indices where entity appears
            entity_name: Name of the entity
            context_lines: Lines of context around each occurrence
            
        Returns:
            List of LogChunk objects
        """
        if context_lines is None:
            context_lines = self.context_lines
        
        if not entity_indices:
            logger.warning(f"No indices provided for entity '{entity_name}'")
            return []
        
        chunks = []
        chunk_id = 0
        
        # Group nearby indices to avoid overlapping chunks
        grouped_indices = self._group_nearby_indices(entity_indices, context_lines * 2)
        
        logger.debug(
            f"Creating entity-context chunks for '{entity_name}': "
            f"{len(entity_indices)} occurrences → {len(grouped_indices)} chunks"
        )
        
        for group in grouped_indices:
            # Find the range to include
            center_idx = int(sum(group) / len(group))  # Average of group
            start_idx = max(0, center_idx - context_lines)
            end_idx = min(len(logs), center_idx + context_lines)
            
            chunk_logs = logs.iloc[start_idx:end_idx]
            chunk = LogChunk(
                logs=chunk_logs,
                chunk_id=chunk_id,
                start_index=start_idx,
                end_index=end_idx,
                focus_entity=entity_name
            )
            
            chunks.append(chunk)
            chunk_id += 1
        
        logger.info(f"Created {len(chunks)} entity-context chunks for '{entity_name}'")
        return chunks
    
    def _group_nearby_indices(
        self,
        indices: List[int],
        max_distance: int
    ) -> List[List[int]]:
        """
        Group indices that are close together.
        
        Args:
            indices: List of indices
            max_distance: Maximum distance to consider indices as "nearby"
            
        Returns:
            List of index groups
        """
        if not indices:
            return []
        
        sorted_indices = sorted(indices)
        groups = []
        current_group = [sorted_indices[0]]
        
        for idx in sorted_indices[1:]:
            if idx - current_group[-1] <= max_distance:
                current_group.append(idx)
            else:
                groups.append(current_group)
                current_group = [idx]
        
        groups.append(current_group)
        return groups
    
    def chunk_by_time_window(
        self,
        logs: pd.DataFrame,
        timestamp_column: str,
        window_minutes: int = 5
    ) -> List[LogChunk]:
        """
        Create chunks based on time windows.
        
        Args:
            logs: DataFrame of log entries
            timestamp_column: Column containing timestamps
            window_minutes: Size of time window in minutes
            
        Returns:
            List of LogChunk objects
        """
        if timestamp_column not in logs.columns:
            logger.warning(f"Timestamp column '{timestamp_column}' not found")
            return []
        
        try:
            # Convert to datetime
            logs = logs.copy()
            logs[timestamp_column] = pd.to_datetime(
                logs[timestamp_column],
                errors='coerce'
            )
            
            # Drop rows with invalid timestamps
            logs = logs.dropna(subset=[timestamp_column])
            
            if len(logs) == 0:
                return []
            
            # Sort by timestamp
            logs = logs.sort_values(timestamp_column)
            
            chunks = []
            chunk_id = 0
            
            # Create time windows
            start_time = logs[timestamp_column].min()
            end_time = logs[timestamp_column].max()
            current_time = start_time
            
            window_delta = pd.Timedelta(minutes=window_minutes)
            
            while current_time <= end_time:
                window_end = current_time + window_delta
                
                # Filter logs in this window
                mask = (
                    (logs[timestamp_column] >= current_time) &
                    (logs[timestamp_column] < window_end)
                )
                window_logs = logs[mask]
                
                if len(window_logs) > 0:
                    chunk = LogChunk(
                        logs=window_logs,
                        chunk_id=chunk_id,
                        start_index=window_logs.index[0],
                        end_index=window_logs.index[-1]
                    )
                    chunks.append(chunk)
                    chunk_id += 1
                
                current_time = window_end
            
            logger.info(
                f"Created {len(chunks)} time-window chunks "
                f"({window_minutes} min windows)"
            )
            return chunks
            
        except Exception as e:
            logger.error(f"Error creating time-window chunks: {e}")
            return []
    
    def merge_overlapping_chunks(
        self,
        chunks: List[LogChunk],
        max_tokens: Optional[int] = None
    ) -> List[LogChunk]:
        """
        Merge overlapping chunks if they fit within token limit.
        
        Args:
            chunks: List of LogChunk objects
            max_tokens: Maximum tokens per merged chunk
            
        Returns:
            List of merged LogChunk objects
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
        
        if len(chunks) <= 1:
            return chunks
        
        merged = []
        current_chunk = chunks[0]
        
        for next_chunk in chunks[1:]:
            # Check if chunks overlap or are adjacent
            if current_chunk.end_index >= next_chunk.start_index:
                # Try to merge
                combined_logs = pd.concat([
                    current_chunk.logs,
                    next_chunk.logs
                ]).drop_duplicates()
                
                # Estimate token count
                estimated_tokens = len(combined_logs.to_string()) / 4
                
                if estimated_tokens <= max_tokens:
                    # Merge successful
                    current_chunk = LogChunk(
                        logs=combined_logs,
                        chunk_id=current_chunk.chunk_id,
                        start_index=current_chunk.start_index,
                        end_index=next_chunk.end_index,
                        focus_entity=current_chunk.focus_entity or next_chunk.focus_entity
                    )
                else:
                    # Can't merge, save current and start new
                    merged.append(current_chunk)
                    current_chunk = next_chunk
            else:
                # No overlap, save current and start new
                merged.append(current_chunk)
                current_chunk = next_chunk
        
        # Add the last chunk
        merged.append(current_chunk)
        
        logger.info(f"Merged {len(chunks)} chunks into {len(merged)} chunks")
        return merged
    
    def smart_chunk(
        self,
        logs: pd.DataFrame,
        entity_indices: Optional[Dict[str, List[int]]] = None,
        prioritize_entities: bool = True
    ) -> List[LogChunk]:
        """
        Smart chunking that combines multiple strategies.
        
        Args:
            logs: DataFrame of log entries
            entity_indices: Optional dict of entity -> indices
            prioritize_entities: If True, create entity-focused chunks first
            
        Returns:
            List of LogChunk objects
        """
        all_chunks = []
        covered_indices = set()
        
        # Strategy 1: Entity-context chunks (if entities provided)
        if entity_indices and prioritize_entities:
            for entity_name, indices in entity_indices.items():
                entity_chunks = self.chunk_by_entity_context(
                    logs,
                    indices,
                    entity_name
                )
                
                for chunk in entity_chunks:
                    all_chunks.append(chunk)
                    covered_indices.update(range(chunk.start_index, chunk.end_index))
        
        # Strategy 2: Size-based chunks for uncovered areas
        if covered_indices:
            # Find gaps
            all_indices = set(range(len(logs)))
            uncovered = sorted(all_indices - covered_indices)
            
            if uncovered:
                # Create contiguous ranges
                ranges = []
                start = uncovered[0]
                end = uncovered[0]
                
                for idx in uncovered[1:]:
                    if idx == end + 1:
                        end = idx
                    else:
                        ranges.append((start, end + 1))
                        start = idx
                        end = idx
                
                ranges.append((start, end + 1))
                
                # Create chunks for each range
                for start, end in ranges:
                    range_logs = logs.iloc[start:end]
                    size_chunks = self.chunk_by_size(range_logs)
                    all_chunks.extend(size_chunks)
        else:
            # No entities, just use size-based chunking
            all_chunks = self.chunk_by_size(logs)
        
        # Re-number chunks
        for i, chunk in enumerate(all_chunks):
            chunk.chunk_id = i
        
        logger.info(f"Smart chunking created {len(all_chunks)} total chunks")
        return all_chunks
    
    def get_chunk_statistics(self, chunks: List[LogChunk]) -> Dict[str, Any]:
        """
        Get statistics about chunks.
        
        Args:
            chunks: List of LogChunk objects
            
        Returns:
            Dictionary with statistics
        """
        if not chunks:
            return {"total_chunks": 0}
        
        token_counts = [chunk.token_estimate for chunk in chunks]
        entry_counts = [len(chunk) for chunk in chunks]
        
        stats = {
            "total_chunks": len(chunks),
            "total_entries": sum(entry_counts),
            "total_tokens": sum(token_counts),
            "avg_tokens_per_chunk": sum(token_counts) / len(chunks),
            "max_tokens": max(token_counts),
            "min_tokens": min(token_counts),
            "avg_entries_per_chunk": sum(entry_counts) / len(chunks),
            "chunks_with_entities": sum(1 for c in chunks if c.focus_entity),
        }
        
        return stats

