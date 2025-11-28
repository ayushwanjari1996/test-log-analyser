"""Parse and validate LLM responses."""

import json
from typing import Dict, Any, List, Optional
from ..utils.logger import setup_logger
from ..utils.exceptions import LLMError

logger = setup_logger()


class ResponseParser:
    """
    Parses and validates JSON responses from LLM.
    """
    
    def __init__(self):
        """Initialize response parser."""
        logger.info("Initialized ResponseParser")
    
    def parse_find_response(self, response_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate FIND mode response.
        
        Expected format:
        {
            "entities_found": ["entity1", "entity2"],
            "next_entities": ["related1", "related2"],
            "relevant_logs": ["log_line_1", "log_line_2"],
            "mode_suggestion": "find|analyze"
        }
        
        Args:
            response_json: JSON response from LLM
            
        Returns:
            Validated and normalized response dictionary
            
        Raises:
            LLMError: If response format is invalid
        """
        try:
            result = {
                "entities_found": response_json.get("entities_found", []),
                "next_entities": response_json.get("next_entities", []),
                "relevant_logs": response_json.get("relevant_logs", []),
                "mode_suggestion": response_json.get("mode_suggestion", "find")
            }
            
            # Validate types
            if not isinstance(result["entities_found"], list):
                result["entities_found"] = []
            
            if not isinstance(result["next_entities"], list):
                result["next_entities"] = []
            
            if not isinstance(result["relevant_logs"], list):
                result["relevant_logs"] = []
            
            if result["mode_suggestion"] not in ["find", "analyze", "trace"]:
                result["mode_suggestion"] = "find"
            
            logger.debug(
                f"Parsed FIND response: {len(result['entities_found'])} entities found, "
                f"{len(result['next_entities'])} next entities"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse FIND response: {e}")
            raise LLMError(f"Invalid FIND response format: {e}")
    
    def parse_analyze_response(self, response_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate ANALYZE mode response.
        
        Expected format:
        {
            "observations": ["observation1", "observation2"],
            "patterns": ["pattern1", "pattern2"],
            "correlations": ["correlation1", "correlation2"],
            "next_entities": ["entity1", "entity2"],
            "confidence": 0.85,
            "mode_suggestion": "find|analyze"
        }
        
        Args:
            response_json: JSON response from LLM
            
        Returns:
            Validated and normalized response dictionary
            
        Raises:
            LLMError: If response format is invalid
        """
        try:
            result = {
                "observations": response_json.get("observations", []),
                "patterns": response_json.get("patterns", []),
                "correlations": response_json.get("correlations", []),
                "next_entities": response_json.get("next_entities", []),
                "confidence": response_json.get("confidence", 0.5),
                "mode_suggestion": response_json.get("mode_suggestion", "analyze")
            }
            
            # Validate types
            for list_field in ["observations", "patterns", "correlations", "next_entities"]:
                if not isinstance(result[list_field], list):
                    result[list_field] = []
            
            # Validate confidence
            if not isinstance(result["confidence"], (int, float)):
                result["confidence"] = 0.5
            else:
                result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
            
            # Validate mode
            if result["mode_suggestion"] not in ["find", "analyze", "trace"]:
                result["mode_suggestion"] = "analyze"
            
            logger.debug(
                f"Parsed ANALYZE response: {len(result['observations'])} observations, "
                f"{len(result['patterns'])} patterns, confidence={result['confidence']:.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse ANALYZE response: {e}")
            raise LLMError(f"Invalid ANALYZE response format: {e}")
    
    def parse_trace_response(self, response_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse and validate TRACE mode response.
        
        Expected format:
        {
            "timeline": [
                {"timestamp": "...", "event": "...", "entity": "..."}
            ],
            "flow_steps": ["step1", "step2", "step3"],
            "next_entities": ["entity1", "entity2"],
            "bottlenecks": ["bottleneck1"],
            "mode_suggestion": "find|analyze"
        }
        
        Args:
            response_json: JSON response from LLM
            
        Returns:
            Validated and normalized response dictionary
            
        Raises:
            LLMError: If response format is invalid
        """
        try:
            result = {
                "timeline": response_json.get("timeline", []),
                "flow_steps": response_json.get("flow_steps", []),
                "next_entities": response_json.get("next_entities", []),
                "bottlenecks": response_json.get("bottlenecks", []),
                "mode_suggestion": response_json.get("mode_suggestion", "trace")
            }
            
            # Validate types
            for list_field in ["timeline", "flow_steps", "next_entities", "bottlenecks"]:
                if not isinstance(result[list_field], list):
                    result[list_field] = []
            
            # Validate mode
            if result["mode_suggestion"] not in ["find", "analyze", "trace"]:
                result["mode_suggestion"] = "trace"
            
            logger.debug(
                f"Parsed TRACE response: {len(result['timeline'])} timeline events, "
                f"{len(result['flow_steps'])} flow steps"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse TRACE response: {e}")
            raise LLMError(f"Invalid TRACE response format: {e}")
    
    def parse_response(
        self,
        response_text: str,
        expected_mode: str = "find"
    ) -> Dict[str, Any]:
        """
        Parse response text based on expected mode.
        
        Args:
            response_text: Raw response text from LLM
            expected_mode: Expected response mode (find/analyze/trace)
            
        Returns:
            Parsed and validated response dictionary
            
        Raises:
            LLMError: If parsing fails
        """
        try:
            # Parse JSON
            response_json = json.loads(response_text)
            
            # Route to appropriate parser
            if expected_mode == "find":
                return self.parse_find_response(response_json)
            elif expected_mode == "analyze":
                return self.parse_analyze_response(response_json)
            elif expected_mode == "trace":
                return self.parse_trace_response(response_json)
            else:
                logger.warning(f"Unknown mode '{expected_mode}', using FIND parser")
                return self.parse_find_response(response_json)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")
            raise LLMError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            raise LLMError(f"Response parsing failed: {e}")
    
    def validate_json_structure(
        self,
        json_data: Dict[str, Any],
        required_fields: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that JSON has required fields.
        
        Args:
            json_data: JSON data to validate
            required_fields: List of required field names
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        missing_fields = [field for field in required_fields if field not in json_data]
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            return False, error_msg
        
        return True, None
    
    def extract_entities_from_response(
        self,
        response: Dict[str, Any]
    ) -> List[str]:
        """
        Extract all entity references from a parsed response.
        
        Args:
            response: Parsed response dictionary
            
        Returns:
            List of unique entity names
        """
        entities = set()
        
        # Check different fields that might contain entities
        if "entities_found" in response:
            entities.update(response["entities_found"])
        
        if "next_entities" in response:
            entities.update(response["next_entities"])
        
        # Extract from timeline if present
        if "timeline" in response:
            for event in response["timeline"]:
                if isinstance(event, dict) and "entity" in event:
                    entities.add(event["entity"])
        
        return list(entities)
    
    def merge_responses(
        self,
        responses: List[Dict[str, Any]],
        mode: str = "find"
    ) -> Dict[str, Any]:
        """
        Merge multiple responses into a single consolidated response.
        
        Args:
            responses: List of parsed response dictionaries
            mode: Response mode
            
        Returns:
            Merged response dictionary
        """
        if not responses:
            return {}
        
        if len(responses) == 1:
            return responses[0]
        
        merged = {}
        
        if mode == "find":
            merged = {
                "entities_found": [],
                "next_entities": [],
                "relevant_logs": [],
                "mode_suggestion": "find"
            }
            
            for response in responses:
                merged["entities_found"].extend(response.get("entities_found", []))
                merged["next_entities"].extend(response.get("next_entities", []))
                merged["relevant_logs"].extend(response.get("relevant_logs", []))
            
            # Deduplicate
            merged["entities_found"] = list(set(merged["entities_found"]))
            merged["next_entities"] = list(set(merged["next_entities"]))
            
        elif mode == "analyze":
            merged = {
                "observations": [],
                "patterns": [],
                "correlations": [],
                "next_entities": [],
                "confidence": 0.0,
                "mode_suggestion": "analyze"
            }
            
            confidences = []
            for response in responses:
                merged["observations"].extend(response.get("observations", []))
                merged["patterns"].extend(response.get("patterns", []))
                merged["correlations"].extend(response.get("correlations", []))
                merged["next_entities"].extend(response.get("next_entities", []))
                confidences.append(response.get("confidence", 0.5))
            
            # Average confidence
            merged["confidence"] = sum(confidences) / len(confidences) if confidences else 0.5
            
            # Deduplicate entities
            merged["next_entities"] = list(set(merged["next_entities"]))
        
        elif mode == "trace":
            merged = {
                "timeline": [],
                "flow_steps": [],
                "next_entities": [],
                "bottlenecks": [],
                "mode_suggestion": "trace"
            }
            
            for response in responses:
                merged["timeline"].extend(response.get("timeline", []))
                merged["flow_steps"].extend(response.get("flow_steps", []))
                merged["next_entities"].extend(response.get("next_entities", []))
                merged["bottlenecks"].extend(response.get("bottlenecks", []))
            
            # Sort timeline by timestamp if possible
            try:
                merged["timeline"].sort(key=lambda x: x.get("timestamp", ""))
            except:
                pass
            
            # Deduplicate
            merged["next_entities"] = list(set(merged["next_entities"]))
        
        logger.info(f"Merged {len(responses)} {mode} responses")
        return merged

