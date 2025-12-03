"""
Smart search tools with term normalization and fuzzy matching.

Enables intelligent search by trying variants of search terms.
"""

import pandas as pd
import yaml
from pathlib import Path
from typing import List, Dict
from .base_tool import Tool, ToolResult, ToolParameter, ParameterType


class NormalizeTermTool(Tool):
    """Expand a search term into normalized variants"""
    
    def __init__(self, config_dir: str = "config"):
        super().__init__(
            name="normalize_term",
            description="Get normalized variants of a search term (e.g., 'registration' → ['registration', 'register', 'reg'])",
            parameters=[
                ToolParameter(
                    name="term",
                    param_type=ParameterType.STRING,
                    description="Term to normalize",
                    required=True,
                    example="registration"
                )
            ]
        )
        self.config_dir = Path(config_dir)
        self.term_mappings = self._load_term_mappings()
    
    def _load_term_mappings(self) -> Dict[str, List[str]]:
        """Load term normalization mappings from config"""
        try:
            path = self.config_dir / "react_config.yaml"
            if path.exists():
                with open(path) as f:
                    config = yaml.safe_load(f)
                    return config.get('term_normalization', {})
        except Exception:
            pass
        
        # Default mappings
        return {
            "registration": ["registration", "register", "registered", "reg"],
            "error": ["error", "err", "fail", "failure", "exception", "critical"],
            "offline": ["offline", "down", "disconnected", "unreachable"],
        }
    
    def execute(self, **kwargs) -> ToolResult:
        term = kwargs.get("term", "").lower()
        
        if not term:
            return ToolResult(
                success=False,
                data=None,
                error="No term provided"
            )
        
        # Check if term has mapping
        if term in self.term_mappings:
            variants = self.term_mappings[term]
            return ToolResult(
                success=True,
                data={"original": term, "variants": variants},
                message=f"Found {len(variants)} variants for '{term}': {', '.join(variants)}",
                metadata={"count": len(variants)}
            )
        
        # No mapping found, return original term
        return ToolResult(
            success=True,
            data={"original": term, "variants": [term]},
            message=f"No normalization mapping for '{term}', using original term",
            metadata={"count": 1}
        )


class FuzzySearchTool(Tool):
    """Search logs with term variants (auto-tries normalized terms)"""
    
    def __init__(self, normalize_tool: NormalizeTermTool, config_dir: str = "config"):
        super().__init__(
            name="fuzzy_search",
            description="Search logs using normalized term variants. Automatically tries variants until finds matches.",
            parameters=[
                ToolParameter(
                    name="logs",
                    param_type=ParameterType.DATAFRAME,
                    description="DataFrame of logs to search (auto-injected)",
                    required=False
                ),
                ToolParameter(
                    name="term",
                    param_type=ParameterType.STRING,
                    description="Search term to find (will try variants)",
                    required=True,
                    example="registration"
                ),
                ToolParameter(
                    name="field",
                    param_type=ParameterType.STRING,
                    description="Specific field to search in (default: all)",
                    required=False,
                    example="_source.log"
                )
            ]
        )
        self.normalize_tool = normalize_tool
    
    def execute(self, **kwargs) -> ToolResult:
        logs = kwargs.get("logs")
        term = kwargs.get("term", "").lower()
        field = kwargs.get("field")
        
        if logs is None or logs.empty:
            return ToolResult(
                success=True,
                data=pd.DataFrame(),
                message="No logs to search",
                metadata={"count": 0}
            )
        
        if not term:
            return ToolResult(
                success=False,
                data=None,
                error="No search term provided"
            )
        
        # Get normalized variants
        norm_result = self.normalize_tool.execute(term=term)
        if not norm_result.success:
            variants = [term]
        else:
            variants = norm_result.data.get("variants", [term])
        
        # Try each variant until we find matches
        all_matches = pd.DataFrame()
        matched_terms = []
        
        for variant in variants:
            # Search for this variant
            if field and field in logs.columns:
                # Search specific field
                mask = logs[field].astype(str).str.contains(variant, case=False, na=False)
                matches = logs[mask]
            else:
                # Search all columns
                mask = logs.astype(str).apply(
                    lambda row: any(variant.lower() in str(cell).lower() for cell in row),
                    axis=1
                )
                matches = logs[mask]
            
            if not matches.empty:
                # Found matches with this variant
                all_matches = pd.concat([all_matches, matches]).drop_duplicates()
                matched_terms.append(variant)
        
        count = len(all_matches)
        
        if count == 0:
            return ToolResult(
                success=True,
                data=all_matches,
                message=f"No logs found matching '{term}' or its variants {variants}",
                metadata={"count": 0, "tried_variants": variants}
            )
        
        return ToolResult(
            success=True,
            data=all_matches,
            message=f"Found {count} logs matching variants of '{term}': {', '.join(matched_terms)}",
            metadata={
                "count": count,
                "original_term": term,
                "matched_variants": matched_terms,
                "tried_variants": variants
            }
        )

