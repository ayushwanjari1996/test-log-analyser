"""Main log analyzer orchestrator coordinating all components."""

from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

from ..core.log_processor import LogProcessor
from ..core.chunker import LogChunker
from ..core.entity_manager import EntityManager
from ..core.llm_query_parser import LLMQueryParser
from ..core.iterative_search import IterativeSearchStrategy
from ..core.llm_bridge_selector import LLMGuidedBridgeSelector
from ..llm import OllamaClient, PromptBuilder, ResponseParser
from ..utils.logger import setup_logger
from ..utils.exceptions import LogFileError, LLMError

logger = setup_logger()


class LogAnalyzer:
    """
    Main orchestrator for log analysis.
    
    Coordinates all components to perform:
    - Entity lookup
    - Relationship search (with iterative exploration)
    - Root cause analysis
    - Flow tracing
    """
    
    def __init__(self, log_file_path: str, use_llm_parsing: bool = True):
        """
        Initialize log analyzer.
        
        Args:
            log_file_path: Path to CSV log file
            use_llm_parsing: Use LLM for query parsing (default: True)
        """
        logger.info(f"Initializing LogAnalyzer for {log_file_path}")
        
        # Core components
        self.processor = LogProcessor(log_file_path)
        self.chunker = LogChunker()
        self.entity_manager = EntityManager()
        
        # LLM components
        self.llm_client = OllamaClient()
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
        
        # Query parsing
        self.query_parser = LLMQueryParser(self.llm_client)
        self.use_llm_parsing = use_llm_parsing
        
        # Iterative search
        self.iterative_searcher = IterativeSearchStrategy(
            processor=self.processor,
            max_iterations=5,
            max_bridges_per_iteration=3
        )
        
        # LLM-guided bridge selection
        self.bridge_selector = LLMGuidedBridgeSelector(
            self.llm_client,
            self.prompt_builder
        )
        
        # State
        self.logs = None
        self.logs_loaded = False
        
        logger.info("LogAnalyzer initialized successfully")
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Main entry point: analyze any user query.
        
        Args:
            query: Natural language query
            
        Returns:
            Analysis results dictionary
        """
        logger.info(f"="*60)
        logger.info(f"Analyzing query: '{query}'")
        logger.info(f"="*60)
        
        start_time = datetime.now()
        
        try:
            # 1. Parse query
            logger.info("Step 1: Parsing query...")
            parsed = self.query_parser.parse_query(query)
            
            # 2. Load logs if not already loaded
            if not self.logs_loaded:
                logger.info("Step 2: Loading logs...")
                self.logs = self.processor.read_all_logs()
                self.logs_loaded = True
                logger.info(f"Loaded {len(self.logs)} log entries")
            
            # 3. Route to appropriate handler based on query type
            query_type = parsed["query_type"]
            search_strategy = parsed.get("search_strategy", "direct")
            
            # Smart corrections for misclassified queries
            secondary = parsed.get("secondary_entity")
            primary = parsed.get("primary_entity")
            
            # Correction 1: "find A for B value" pattern → relationship
            if (secondary and secondary.get("value") and 
                primary and not primary.get("value") and 
                query_type == "specific_value"):
                logger.info("Correcting query type: specific_value → relationship (detected 'find A for B x' pattern)")
                query_type = "relationship"
            
            # Correction 2: Analysis keywords → analysis
            analysis_keywords = ["why", "analyse", "analyze", "debug", "investigate", "troubleshoot", "diagnose"]
            if any(kw in query.lower() for kw in analysis_keywords):
                if query_type != "analysis":
                    logger.info(f"Correcting query type: {query_type} → analysis (detected analysis keyword)")
                    query_type = "analysis"
                
                # Extract entity value from query using regex (MAC, IP, IDs, etc.)
                import re
                # Try to find MAC address
                mac_match = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', query)
                # Try to find IP address
                ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', query)
                # Try to find hex ID
                hex_match = re.search(r'0x[0-9a-fA-F]+', query)
                # Try to find simple ID pattern
                id_match = re.search(r'\b[A-Z0-9]{6,}\b', query)
                
                entity_value = None
                if mac_match:
                    entity_value = mac_match.group(0)
                elif ip_match:
                    entity_value = ip_match.group(0)
                elif hex_match:
                    entity_value = hex_match.group(0)
                elif id_match:
                    entity_value = id_match.group(0)
                
                if entity_value:
                    logger.info(f"Extracted entity value from query: {entity_value}")
                    # Update primary entity with the extracted value
                    if primary:
                        primary["value"] = entity_value
                    else:
                        parsed["primary_entity"] = {"type": "unknown", "value": entity_value, "reasoning": "Extracted from query"}
            
            logger.info(f"Step 3: Executing {query_type} query (strategy: {search_strategy})")
            
            if query_type == "specific_value":
                result = self._execute_specific_search(parsed)
            elif query_type == "aggregation":
                result = self._execute_aggregation_search(parsed)
            elif query_type == "relationship":
                result = self._execute_relationship_search(parsed)
            elif query_type == "analysis":
                result = self._execute_analysis(parsed)
            elif query_type == "trace":
                result = self._execute_trace(parsed)
            else:
                # Fallback to specific search
                result = self._execute_specific_search(parsed)
            
            # Add metadata
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result["query"] = query
            result["parsed_query"] = parsed
            result["duration_seconds"] = duration
            result["timestamp"] = end_time.isoformat()
            
            logger.info(f"Query completed in {duration:.2f}s")
            logger.info(f"="*60)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing query: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "query": query,
                "error": str(e),
                "success": False,
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
    
    def _execute_specific_search(self, parsed: Dict) -> Dict[str, Any]:
        """
        Execute specific value search.
        Example: "find cm CM12345"
        """
        entity = parsed["primary_entity"]
        entity_value = entity.get("value")
        
        # If no value, try secondary entity
        if not entity_value:
            secondary = parsed.get("secondary_entity")
            if secondary and secondary.get("value"):
                entity_value = secondary["value"]
                logger.info(f"Using secondary entity value: {entity_value}")
        
        if not entity_value:
            return {
                "query_type": "specific_value",
                "entity": None,
                "total_occurrences": 0,
                "related_entities": {},
                "sample_logs": [],
                "success": False,
                "error": "No entity value found in query"
            }
        
        logger.info(f"Searching for specific value: {entity_value}")
        
        # Search for value in all columns
        filtered = self.processor.search_text(self.logs, entity_value)
        
        logger.info(f"Found {len(filtered)} logs containing '{entity_value}'")
        
        # Extract related entities
        related_entities = {}
        if len(filtered) > 0:
            from ..utils.config import config
            entity_types = list(config.entity_mappings.get("patterns", {}).keys())
            
            for etype in entity_types:
                entities = self.processor.extract_entities(filtered, etype)
                if entities:
                    related_entities[etype] = list(entities.keys())
        
        return {
            "query_type": "specific_value",
            "entity": entity_value,
            "total_occurrences": len(filtered),
            "related_entities": related_entities,
            "sample_logs": filtered.head(10).to_dict('records') if len(filtered) > 0 else [],
            "success": len(filtered) > 0
        }
    
    def _execute_aggregation_search(self, parsed: Dict) -> Dict[str, Any]:
        """
        Execute aggregation search.
        Example: "find all cms", "list all modems with errors"
        """
        entity_type = parsed["primary_entity"]["type"]
        filters = parsed.get("filter_conditions", [])
        
        logger.info(f"Extracting all instances of type: {entity_type}")
        
        # Extract all entities of this type
        entities = self.processor.extract_entities(self.logs, entity_type)
        
        logger.info(f"Found {len(entities)} unique {entity_type} entities")
        
        # Apply filters if specified
        if filters:
            logger.info(f"Applying filters: {filters}")
            filtered_entities = {}
            
            for entity_value, indices in entities.items():
                entity_logs = self.logs.iloc[indices]
                
                # Check if any log matches filters
                has_filter = False
                for filter_term in filters:
                    mask = entity_logs.astype(str).apply(
                        lambda row: any(filter_term.lower() in str(cell).lower() for cell in row),
                        axis=1
                    )
                    if mask.any():
                        has_filter = True
                        break
                
                if has_filter:
                    filtered_entities[entity_value] = indices
            
            entities = filtered_entities
            logger.info(f"After filtering: {len(entities)} entities")
        
        # Build result
        entity_list = [
            {
                "value": value,
                "occurrences": len(indices),
                "sample_indices": indices[:5]
            }
            for value, indices in entities.items()
        ]
        
        # Sort by occurrences
        entity_list = sorted(entity_list, key=lambda x: x["occurrences"], reverse=True)
        
        return {
            "query_type": "aggregation",
            "entity_type": entity_type,
            "total_found": len(entities),
            "filters_applied": filters,
            "entities": entity_list,
            "success": len(entities) > 0
        }
    
    def _execute_relationship_search(self, parsed: Dict) -> Dict[str, Any]:
        """
        Execute relationship search with iterative exploration.
        Example: "find mdid for cm x"
        """
        target_type = parsed["primary_entity"]["type"]
        source = parsed["secondary_entity"]
        
        if not source:
            logger.warning("No source entity for relationship search, falling back to specific search")
            return self._execute_specific_search(parsed)
        
        source_value = source["value"]
        source_type = source["type"]
        
        logger.info(f"Relationship search: find {target_type} for {source_type}:{source_value}")
        
        # Use iterative search with LLM-guided bridge selection
        # For now, use regular iterative search (LLM bridge selection is optional)
        result = self.iterative_searcher.find_with_bridges(
            logs=self.logs,
            target_entity_type=target_type,
            source_entity_value=source_value,
            source_entity_type=source_type
        )
        
        return {
            "query_type": "relationship",
            "source": {"type": source_type, "value": source_value},
            "target": {"type": target_type, "values": result["target_values"]},
            "found": result["found"],
            "search_path": result["path"],
            "iterations": result["iterations"],
            "bridge_entities": result["bridge_entities"],
            "confidence": result["confidence"],
            "logs_searched": result["logs_searched"],
            "success": result["found"]
        }
    
    def _execute_analysis(self, parsed: Dict) -> Dict[str, Any]:
        """
        Execute root cause analysis.
        Example: "why did cm x fail"
        """
        entity = parsed["primary_entity"]
        entity_value = entity.get("value")
        
        # Fallback: if no value, try to extract from entity type or query
        if not entity_value:
            # Try secondary entity
            secondary = parsed.get("secondary_entity")
            if secondary and secondary.get("value"):
                entity_value = secondary["value"]
                logger.info(f"Using secondary entity value for analysis: {entity_value}")
            else:
                # Last resort: extract last meaningful word from query
                import re
                words = re.findall(r'\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b|\b\S+\b', parsed["original_query"])
                if words:
                    entity_value = words[-1]
                    logger.warning(f"Fallback: using '{entity_value}' from query for analysis")
        
        logger.info(f"Performing root cause analysis for: {entity_value}")
        
        # Get logs for entity
        filtered = self.processor.search_text(self.logs, entity_value)
        
        if len(filtered) == 0:
            return {
                "query_type": "analysis",
                "entity": entity_value,
                "success": False,
                "error": f"No logs found for '{entity_value}'"
            }
        
        logger.info(f"Found {len(filtered)} logs for analysis")
        
        # Chunk logs
        chunks = self.chunker.chunk_by_size(filtered, max_tokens=3000)
        logger.info(f"Created {len(chunks)} chunks for analysis")
        
        # Analyze each chunk
        all_observations = []
        all_patterns = []
        
        for i, chunk in enumerate(chunks[:3]):  # Limit to first 3 chunks
            logger.info(f"Analyzing chunk {i+1}/{min(3, len(chunks))}")
            
            log_text = self.prompt_builder.format_log_chunk(chunk.logs.to_dict('records'))
            
            system, user = self.prompt_builder.build_analyze_prompt(
                user_query=parsed["original_query"],
                log_chunk=log_text,
                focus_entities=[entity_value]
            )
            
            try:
                response = self.llm_client.generate_json(user, system_prompt=system)
                logger.debug(f"LLM response for chunk {i+1}: {response}")
                parsed_response = self.response_parser.parse_analyze_response(response)
                
                obs = parsed_response.get("observations", [])
                pat = parsed_response.get("patterns", [])
                logger.info(f"Chunk {i+1}: {len(obs)} observations, {len(pat)} patterns")
                
                all_observations.extend(obs)
                all_patterns.extend(pat)
            except Exception as e:
                logger.error(f"LLM analysis failed for chunk {i+1}: {e}")
                import traceback
                traceback.print_exc()
        
        # Mark as success if we actually analyzed logs, even if no observations found
        success = len(filtered) > 0 and len(chunks) > 0
        
        return {
            "query_type": "analysis",
            "entity": entity_value,
            "total_logs": len(filtered),
            "chunks_analyzed": min(3, len(chunks)),
            "observations": all_observations,
            "patterns": list(set(all_patterns)),  # Deduplicate
            "success": success
        }
    
    def _execute_trace(self, parsed: Dict) -> Dict[str, Any]:
        """
        Execute flow trace.
        Example: "trace cm x"
        """
        entity = parsed["primary_entity"]
        entity_value = entity["value"]
        
        logger.info(f"Tracing flow for: {entity_value}")
        
        # Get logs for entity
        filtered = self.processor.search_text(self.logs, entity_value)
        
        if len(filtered) == 0:
            return {
                "query_type": "trace",
                "entity": entity_value,
                "success": False,
                "error": f"No logs found for '{entity_value}'"
            }
        
        # Sort by timestamp if available
        if "timestamp" in filtered.columns:
            filtered = filtered.sort_values("timestamp")
        
        logger.info(f"Found {len(filtered)} logs for trace")
        
        # Extract timeline
        timeline = []
        for idx, row in filtered.iterrows():
            timeline.append({
                "timestamp": str(row.get("timestamp", "")),
                "severity": str(row.get("severity", "")),
                "module": str(row.get("module", "")),
                "message": str(row.get("message", ""))
            })
        
        return {
            "query_type": "trace",
            "entity": entity_value,
            "total_events": len(timeline),
            "timeline": timeline,
            "success": True
        }

