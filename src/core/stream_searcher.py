"""
Streaming CSV Search Engine

Fast, memory-efficient search without loading entire file into memory.
"""

import csv
import json
import re
from typing import List, Dict, Any, Optional, Iterator
from pathlib import Path
import pandas as pd

from ..utils.logger import setup_logger
from ..utils.exceptions import LogFileError

logger = setup_logger()


class StreamSearcher:
    """
    Stream-based CSV search engine.
    
    Searches CSV files line-by-line without loading entire file into memory.
    Supports:
    - Plain text search in any column
    - JSON field search (for _source.log column)
    - Regex patterns
    - Case-sensitive/insensitive search
    """
    
    def __init__(self, csv_file_path: str):
        """
        Initialize stream searcher.
        
        Args:
            csv_file_path: Path to CSV log file
        """
        self.csv_file_path = Path(csv_file_path)
        
        if not self.csv_file_path.exists():
            raise LogFileError(f"CSV file not found: {csv_file_path}")
        
        # Read header to get column names
        with open(self.csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            self.headers = next(reader)
        
        logger.info(f"StreamSearcher initialized for {csv_file_path}")
        logger.debug(f"CSV has {len(self.headers)} columns")
    
    def search(
        self,
        search_term: str,
        columns: Optional[List[str]] = None,
        case_sensitive: bool = False,
        regex: bool = False,
        max_results: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Search CSV file line-by-line.
        
        Args:
            search_term: Text/pattern to search for
            columns: Specific columns to search (None = all columns)
            case_sensitive: Case-sensitive matching
            regex: Treat search_term as regex pattern
            max_results: Stop after N matches (None = unlimited)
            
        Returns:
            DataFrame with matching rows
        """
        logger.info(f"Streaming search for: '{search_term}' "
                   f"(case_sensitive={case_sensitive}, regex={regex})")
        
        # Compile regex pattern if needed
        if regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(search_term, flags)
            except re.error as e:
                logger.error(f"Invalid regex pattern: {e}")
                return pd.DataFrame()
        else:
            # For plain text, prepare comparison term
            compare_term = search_term if case_sensitive else search_term.lower()
        
        # Determine which column indices to search
        if columns:
            search_indices = [
                i for i, col in enumerate(self.headers) 
                if col in columns
            ]
        else:
            search_indices = list(range(len(self.headers)))
        
        logger.debug(f"Searching in {len(search_indices)} columns")
        
        # Stream through file and collect matches
        matches = []
        line_num = 0
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    line_num += 1
                    
                    # Check if this row matches
                    if self._row_matches(row, search_term, search_indices, 
                                        case_sensitive, regex, pattern if regex else None):
                        matches.append(row)
                        
                        # Stop if we hit max_results
                        if max_results and len(matches) >= max_results:
                            logger.debug(f"Hit max_results limit: {max_results}")
                            break
        
        except Exception as e:
            logger.error(f"Error during streaming search: {e}")
            return pd.DataFrame()
        
        logger.info(f"Found {len(matches)} matches out of {line_num} lines scanned")
        
        # Convert to DataFrame
        if matches:
            df = pd.DataFrame(matches, columns=self.headers)
            return df
        else:
            return pd.DataFrame(columns=self.headers)
    
    def _row_matches(
        self,
        row: List[str],
        search_term: str,
        search_indices: List[int],
        case_sensitive: bool,
        is_regex: bool,
        pattern: Optional[re.Pattern] = None
    ) -> bool:
        """
        Check if a row matches the search criteria.
        
        Args:
            row: CSV row as list of strings
            search_term: Search term
            search_indices: Column indices to search
            case_sensitive: Case-sensitive matching
            is_regex: Whether using regex
            pattern: Compiled regex pattern (if is_regex=True)
            
        Returns:
            True if row matches
        """
        for idx in search_indices:
            if idx >= len(row):
                continue
            
            cell_value = row[idx]
            
            # Try to parse JSON if this looks like a JSON column
            if cell_value.strip().startswith('{'):
                try:
                    json_data = json.loads(cell_value)
                    # Search within JSON values
                    json_str = json.dumps(json_data)
                    if self._value_matches(json_str, search_term, case_sensitive, 
                                          is_regex, pattern):
                        return True
                except json.JSONDecodeError:
                    pass
            
            # Regular text search
            if self._value_matches(cell_value, search_term, case_sensitive, 
                                  is_regex, pattern):
                return True
        
        return False
    
    def _value_matches(
        self,
        value: str,
        search_term: str,
        case_sensitive: bool,
        is_regex: bool,
        pattern: Optional[re.Pattern]
    ) -> bool:
        """
        Check if a value matches the search term.
        
        Args:
            value: String value to check
            search_term: Search term
            case_sensitive: Case-sensitive matching
            is_regex: Whether using regex
            pattern: Compiled regex pattern
            
        Returns:
            True if matches
        """
        if is_regex:
            return pattern.search(value) is not None
        else:
            if case_sensitive:
                return search_term in value
            else:
                return search_term.lower() in value.lower()
    
    def count_matches(
        self,
        search_term: str,
        columns: Optional[List[str]] = None,
        case_sensitive: bool = False
    ) -> int:
        """
        Count matching rows without loading all data.
        
        Args:
            search_term: Text to search for
            columns: Columns to search (None = all)
            case_sensitive: Case-sensitive matching
            
        Returns:
            Number of matching rows
        """
        logger.info(f"Counting matches for: '{search_term}'")
        
        # Prepare search term
        compare_term = search_term if case_sensitive else search_term.lower()
        
        # Determine which columns to search
        if columns:
            search_indices = [
                i for i, col in enumerate(self.headers) 
                if col in columns
            ]
        else:
            search_indices = list(range(len(self.headers)))
        
        count = 0
        
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                for row in reader:
                    if self._row_matches(row, search_term, search_indices, 
                                        case_sensitive, False, None):
                        count += 1
        
        except Exception as e:
            logger.error(f"Error counting matches: {e}")
            return 0
        
        logger.info(f"Found {count} matches")
        return count

