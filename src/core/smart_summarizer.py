"""
Smart Summarizer for Log Analysis.

Intelligently compresses large log datasets into compact, entity-aware summaries
that fit in LLM context while preserving important information.
"""

import json
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from datetime import datetime
import pandas as pd
import re

logger = logging.getLogger(__name__)


class EntityExtractor:
    """
    Extract entities from logs using entity_mappings.yaml.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize entity extractor.
        
        Args:
            config_dir: Path to config directory containing entity_mappings.yaml
        """
        self.config_dir = config_dir
        self.entity_config = self._load_entity_config()
        self.field_to_entity = self._build_field_mapping()
    
    def _load_entity_config(self) -> Dict[str, Any]:
        """Load entity mappings configuration."""
        try:
            mapping_file = Path(self.config_dir) / "entity_mappings.yaml"
            with open(mapping_file, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Failed to load entity_mappings.yaml: {e}")
            return {"aliases": {}, "relationships": {}, "patterns": {}}
    
    def _build_field_mapping(self) -> Dict[str, str]:
        """Build reverse mapping: field_name -> entity_type."""
        mapping = {}
        for entity_type, aliases in self.entity_config.get('aliases', {}).items():
            for alias in aliases:
                mapping[alias.lower()] = entity_type
        return mapping
    
    def extract_from_logs(self, logs: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        Extract all entities from logs.
        
        Args:
            logs: DataFrame with logs
            
        Returns:
            Dict of entity_type -> {value: count}
        """
        entities = defaultdict(Counter)
        
        if logs.empty or '_source.log' not in logs.columns:
            return dict(entities)
        
        for log_entry in logs['_source.log']:
            try:
                # Parse JSON (handle double-escaped quotes)
                json_str = self._extract_json(log_entry)
                if not json_str:
                    continue
                
                log_json = json.loads(json_str)
                
                # Extract each field
                for field_name, field_value in log_json.items():
                    # Skip empty or null
                    if not field_value or field_value in ['<null>', 'null', '']:
                        continue
                    
                    # Check if this is an entity field
                    entity_type = self.field_to_entity.get(field_name.lower())
                    if entity_type:
                        entities[entity_type][str(field_value)] += 1
                        
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"Failed to parse log: {e}")
                continue
        
        return {k: dict(v) for k, v in entities.items()}
    
    def _extract_json(self, log_entry: str) -> Optional[str]:
        """Extract and unescape JSON from log entry."""
        if not isinstance(log_entry, str):
            return None
        
        # Find JSON start
        json_start = log_entry.find('{')
        if json_start == -1:
            return None
        
        # Extract and unescape
        json_str = log_entry[json_start:]
        json_str = json_str.replace('""', '"')
        
        return json_str


class LogAggregator:
    """
    Aggregate logs by entities and calculate statistics.
    """
    
    def aggregate(self, logs: pd.DataFrame, entities: Dict[str, Dict[str, int]]) -> Dict[str, Any]:
        """
        Aggregate logs and compute statistics.
        
        Args:
            logs: DataFrame with logs
            entities: Extracted entities from EntityExtractor
            
        Returns:
            Dict with aggregation results
        """
        stats = {
            "total_count": len(logs),
            "entities": {},
            "severity_dist": {},
            "time_range": None,
            "top_functions": {},
            "top_messages": {}
        }
        
        if logs.empty:
            return stats
        
        # Entity statistics
        for entity_type, values in entities.items():
            sorted_values = sorted(values.items(), key=lambda x: x[1], reverse=True)
            stats["entities"][entity_type] = {
                "unique_count": len(values),
                "total_count": sum(values.values()),
                "top_5": sorted_values[:5]
            }
        
        # Parse logs for severity, functions, messages
        severities = []
        functions = []
        messages = []
        timestamps = []
        
        if '_source.log' in logs.columns:
            for log_entry in logs['_source.log']:
                try:
                    json_str = self._extract_json(log_entry)
                    if not json_str:
                        continue
                    
                    log_json = json.loads(json_str)
                    
                    if 'Severity' in log_json:
                        severities.append(log_json['Severity'])
                    if 'Function' in log_json:
                        functions.append(log_json['Function'])
                    if 'Message' in log_json:
                        messages.append(log_json['Message'])
                        
                except (json.JSONDecodeError, TypeError):
                    continue
        
        # Severity distribution
        if severities:
            sev_counter = Counter(severities)
            stats["severity_dist"] = dict(sev_counter.most_common())
        
        # Top functions
        if functions:
            func_counter = Counter(functions)
            stats["top_functions"] = dict(func_counter.most_common(5))
        
        # Top messages
        if messages:
            msg_counter = Counter(messages)
            stats["top_messages"] = dict(msg_counter.most_common(5))
        
        # Time range
        if '_source.@timestamp' in logs.columns:
            try:
                times = pd.to_datetime(logs['_source.@timestamp'], 
                                      format="%b %d, %Y @ %H:%M:%S.%f", 
                                      errors='coerce')
                if not times.isna().all():
                    stats["time_range"] = {
                        "earliest": str(times.min()),
                        "latest": str(times.max()),
                        "span": str(times.max() - times.min())
                    }
            except Exception as e:
                logger.debug(f"Failed to parse timestamps: {e}")
        
        return stats
    
    def _extract_json(self, log_entry: str) -> Optional[str]:
        """Extract and unescape JSON from log entry."""
        if not isinstance(log_entry, str):
            return None
        
        json_start = log_entry.find('{')
        if json_start == -1:
            return None
        
        json_str = log_entry[json_start:].replace('""', '"')
        return json_str


class SmartSampler:
    """
    Select representative log samples using intelligent strategies.
    """
    
    def __init__(self, max_samples: int = 10, importance_weight: float = 0.6):
        """
        Initialize sampler.
        
        Args:
            max_samples: Maximum number of samples to return
            importance_weight: Weight for importance sampling (0-1)
        """
        self.max_samples = max_samples
        self.importance_weight = importance_weight
        self.diversity_weight = 1.0 - importance_weight
    
    def sample(self, logs: pd.DataFrame, entities: Dict[str, Dict[str, int]]) -> List[Dict[str, Any]]:
        """
        Select representative log samples.
        
        Args:
            logs: DataFrame with logs
            entities: Extracted entities
            
        Returns:
            List of sampled log dictionaries
        """
        if logs.empty:
            return []
        
        # Calculate scores for each log
        log_scores = []
        
        for idx, row in logs.iterrows():
            score = self._calculate_log_score(row, entities)
            log_scores.append((idx, score, row))
        
        # Sort by score
        log_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select top N
        selected_logs = []
        for idx, score, row in log_scores[:self.max_samples]:
            log_dict = self._row_to_dict(row)
            if log_dict:
                selected_logs.append(log_dict)
        
        return selected_logs
    
    def _calculate_log_score(self, row: pd.Series, entities: Dict[str, Dict[str, int]]) -> float:
        """
        Calculate importance score for a log entry.
        
        Higher score = more important
        """
        score = 0.0
        
        # Parse log JSON
        if '_source.log' not in row:
            return score
        
        try:
            json_str = self._extract_json(row['_source.log'])
            if not json_str:
                return score
            
            log_json = json.loads(json_str)
            
            # Importance factors
            
            # 1. Severity (ERROR > WARN > INFO > DEBUG)
            severity = log_json.get('Severity', 'INFO')
            severity_scores = {'ERROR': 10, 'WARN': 5, 'INFO': 1, 'DEBUG': 0.5}
            score += severity_scores.get(severity, 0) * self.importance_weight
            
            # 2. Rare entities (inverse frequency)
            for entity_type, values in entities.items():
                for field_name, field_value in log_json.items():
                    if str(field_value) in values:
                        # Rare entities get higher score
                        frequency = values[str(field_value)]
                        rarity_score = 1.0 / (frequency + 1)  # Avoid division by zero
                        score += rarity_score * self.diversity_weight
            
            # 3. Multiple entities (relationship logs)
            entity_count = sum(1 for field in log_json.keys() 
                             if any(field in aliases for aliases in entities.values()))
            score += entity_count * 0.5
            
        except (json.JSONDecodeError, TypeError):
            pass
        
        return score
    
    def _row_to_dict(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """Convert DataFrame row to dict with parsed JSON."""
        try:
            log_dict = {}
            
            # Parse JSON
            if '_source.log' in row:
                json_str = self._extract_json(row['_source.log'])
                if json_str:
                    log_json = json.loads(json_str)
                    log_dict.update(log_json)
            
            # Add timestamp if available
            if '_source.@timestamp' in row:
                log_dict['timestamp'] = row['_source.@timestamp']
            
            return log_dict if log_dict else None
            
        except Exception:
            return None
    
    def _extract_json(self, log_entry: str) -> Optional[str]:
        """Extract and unescape JSON from log entry."""
        if not isinstance(log_entry, str):
            return None
        
        json_start = log_entry.find('{')
        if json_start == -1:
            return None
        
        json_str = log_entry[json_start:].replace('""', '"')
        return json_str


class SummaryFormatter:
    """
    Format aggregated data into human-readable summary for LLM.
    """
    
    def format(self, stats: Dict[str, Any], samples: List[Dict[str, Any]]) -> str:
        """
        Format summary as compact text.
        
        Args:
            stats: Aggregation statistics
            samples: Sample logs
            
        Returns:
            Formatted summary string
        """
        lines = []
        
        # Header
        lines.append(f"📊 Found {stats['total_count']} logs")
        
        # Time range
        if stats.get('time_range'):
            tr = stats['time_range']
            lines.append(f"⏱️  Time: {tr.get('earliest', 'N/A')} → {tr.get('latest', 'N/A')} (span: {tr.get('span', 'N/A')})")
        
        # Entities
        if stats.get('entities'):
            lines.append("\n🔍 Key Entities:")
            for entity_type, entity_data in stats['entities'].items():
                unique = entity_data['unique_count']
                total = entity_data['total_count']
                top_5 = entity_data.get('top_5', [])
                
                top_str = ", ".join([f"{val}({cnt})" for val, cnt in top_5[:3]])
                more = f" +{len(top_5)-3} more" if len(top_5) > 3 else ""
                
                lines.append(f"  • {entity_type}: {unique} unique, {total} total | Top: {top_str}{more}")
        
        # Severity distribution
        if stats.get('severity_dist'):
            sev_str = ", ".join([f"{k}:{v}" for k, v in stats['severity_dist'].items()])
            lines.append(f"\n⚠️  Severities: {sev_str}")
        
        # Top functions
        if stats.get('top_functions'):
            func_str = ", ".join([f"{k}({v})" for k, v in list(stats['top_functions'].items())[:3]])
            lines.append(f"\n⚙️  Top Functions: {func_str}")
        
        # Sample logs
        if samples:
            lines.append(f"\n📝 Top {len(samples)} Sample Logs:")
            for i, sample in enumerate(samples[:10], 1):
                severity = sample.get('Severity', 'N/A')
                function = sample.get('Function', 'N/A')
                message = sample.get('Message', '')
                
                # Truncate message if too long
                if len(message) > 60:
                    message = message[:57] + "..."
                
                lines.append(f"  {i}. [{severity}] {function}: {message}")
        
        # Footer
        lines.append("\n✅ Full data cached for next tool")
        
        return "\n".join(lines)


class SmartSummarizer:
    """
    Main smart summarizer that orchestrates all components.
    """
    
    def __init__(self, 
                 config_dir: str = "config",
                 max_samples: int = 10,
                 importance_weight: float = 0.6):
        """
        Initialize smart summarizer.
        
        Args:
            config_dir: Path to config directory
            max_samples: Maximum sample logs to include
            importance_weight: Weight for importance sampling (0-1)
        """
        self.entity_extractor = EntityExtractor(config_dir)
        self.aggregator = LogAggregator()
        self.sampler = SmartSampler(max_samples, importance_weight)
        self.formatter = SummaryFormatter()
    
    def summarize(self, logs: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate smart summary of logs.
        
        Args:
            logs: DataFrame with logs to summarize
            
        Returns:
            Dict with:
                - summary_text: Formatted text for LLM
                - entities: Extracted entities
                - stats: Aggregation statistics
                - samples: Representative log samples
        """
        try:
            # Handle edge cases
            if logs is None or (isinstance(logs, pd.DataFrame) and logs.empty):
                return {
                    "summary_text": "No logs to summarize",
                    "entities": {},
                    "stats": {"total_count": 0},
                    "samples": []
                }
            
            # Step 1: Extract entities
            entities = self.entity_extractor.extract_from_logs(logs)
            
            # Step 2: Aggregate
            stats = self.aggregator.aggregate(logs, entities)
            
            # Step 3: Smart sample
            samples = self.sampler.sample(logs, entities)
            
            # Step 4: Format
            summary_text = self.formatter.format(stats, samples)
            
            return {
                "summary_text": summary_text,
                "entities": entities,
                "stats": stats,
                "samples": samples
            }
            
        except Exception as e:
            logger.error(f"Summarization failed: {e}", exc_info=True)
            return {
                "summary_text": f"Summarization error: {str(e)}",
                "entities": {},
                "stats": {"total_count": len(logs) if isinstance(logs, pd.DataFrame) else 0},
                "samples": []
            }

