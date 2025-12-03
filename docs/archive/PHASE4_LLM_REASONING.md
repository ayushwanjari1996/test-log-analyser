# Phase 4: LLM-Guided Iterative Exploration

## Problem: How to Choose Next Entity to Explore?

### Current Approach (Simple Ranking)
```
Bridge entities found: [rpdname:RPD001, dc_id:DC123, sf_id:SF456, ip:192.168.1.1]
    ↓
Rank by static scores (IP=9, RPD=8, DC=5, SF=6)
    ↓
Try in order: IP → RPD → DC → SF
```

**Problem:** This is DUMB! It doesn't consider:
- What we're looking for (mdid vs mac vs error)
- Context of the logs
- Semantic relationships between entities
- Which path is most likely to succeed

### Better Approach: LLM Reasoning
```
Query: "find mdid for cm x"
Bridge entities: [rpdname:RPD001, dc_id:DC123, sf_id:SF456, ip:192.168.1.1]
    ↓
Ask LLM: "Which entity is most likely connected to mdid?"
    ↓
LLM reasons:
  "mdid (Modem ID) is typically associated with the modem's provisioning
   and configuration. RPD (Remote PHY Device) manages multiple modems and
   their IDs. DC (Downstream Channel) and SF (Service Flow) are lower-level
   constructs. IP address is a network identifier but less directly related
   to modem ID assignment.
   
   Most likely path: rpdname → mdid
   Second best: ip_address → mdid
   Less likely: dc_id, sf_id"
    ↓
Prioritized order: RPD → IP → DC → SF
```

## LLM Reasoning Integration

### 1. Bridge Selector with LLM Reasoning

```python
class LLMGuidedBridgeSelector:
    """
    Uses LLM to intelligently select which bridge entity to explore next.
    """
    
    def __init__(self, llm_client: OllamaClient, prompt_builder: PromptBuilder):
        self.llm = llm_client
        self.prompt_builder = prompt_builder
        self.reasoning_cache = {}  # Cache LLM decisions
    
    def select_next_bridge(
        self,
        query: str,
        source_entity: Dict[str, str],  # {"type": "cm", "value": "x"}
        target_entity_type: str,  # "mdid"
        bridge_candidates: List[Dict],  # [{"type": "rpdname", "value": "RPD001"}, ...]
        context_logs: pd.DataFrame,  # Logs where source was found
        iteration: int
    ) -> List[Dict]:
        """
        Use LLM to rank bridge entities by likelihood of leading to target.
        
        Returns: Sorted list of bridge entities with reasoning
        """
        # Create cache key
        cache_key = (
            source_entity["type"],
            target_entity_type,
            tuple(sorted([(b["type"], b["value"]) for b in bridge_candidates]))
        )
        
        if cache_key in self.reasoning_cache:
            logger.info("Using cached LLM reasoning")
            return self.reasoning_cache[cache_key]
        
        # Build reasoning prompt
        prompt = self._build_reasoning_prompt(
            query=query,
            source_entity=source_entity,
            target_entity_type=target_entity_type,
            bridge_candidates=bridge_candidates,
            context_logs=context_logs,
            iteration=iteration
        )
        
        # Get LLM reasoning
        logger.info(f"Asking LLM to reason about bridge selection...")
        
        try:
            response = self.llm.generate_json(
                prompt=prompt,
                temperature=0.3,  # Lower temperature for more deterministic reasoning
                max_tokens=500
            )
            
            # Parse LLM response
            ranked_bridges = self._parse_reasoning_response(response, bridge_candidates)
            
            # Cache the result
            self.reasoning_cache[cache_key] = ranked_bridges
            
            return ranked_bridges
            
        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}, falling back to static ranking")
            return self._static_ranking(bridge_candidates)
    
    def _build_reasoning_prompt(
        self,
        query: str,
        source_entity: Dict,
        target_entity_type: str,
        bridge_candidates: List[Dict],
        context_logs: pd.DataFrame,
        iteration: int
    ) -> str:
        """
        Build prompt asking LLM to reason about bridge selection.
        """
        # Format bridge candidates
        bridges_str = "\n".join([
            f"- {b['type']}: {b['value']}"
            for b in bridge_candidates
        ])
        
        # Get sample log context
        sample_logs = context_logs.head(5).to_dict('records')
        logs_str = self.prompt_builder.format_log_chunk(sample_logs)
        
        prompt = f"""You are a log analysis expert helping find entity relationships.

QUERY: {query}

CURRENT SITUATION:
- We are looking for: {target_entity_type}
- We started with: {source_entity['type']} = {source_entity['value']}
- We found these logs containing {source_entity['value']}
- The target '{target_entity_type}' was NOT found directly in these logs
- This is iteration {iteration} of our search

SAMPLE LOGS:
{logs_str}

BRIDGE ENTITIES EXTRACTED:
{bridges_str}

TASK:
Reason about which bridge entity is most likely to lead us to '{target_entity_type}'.
Consider:
1. Semantic relationships (which entities are typically connected?)
2. Technical domain knowledge (cable modem systems, networking, provisioning)
3. Log context (what do these logs tell us?)
4. Entity specificity (more specific entities are better bridges)

Respond in JSON format:
{{
  "reasoning": "Explain your thought process",
  "ranked_bridges": [
    {{
      "type": "entity_type",
      "value": "entity_value",
      "confidence": 0.9,
      "rationale": "Why this is the best choice"
    }},
    ...
  ],
  "alternative_strategy": "If these bridges fail, what else could we try?"
}}"""
        
        return prompt
    
    def _parse_reasoning_response(
        self,
        response: Dict,
        original_candidates: List[Dict]
    ) -> List[Dict]:
        """
        Parse LLM reasoning and create ranked bridge list.
        """
        ranked = []
        
        reasoning = response.get("reasoning", "")
        bridges = response.get("ranked_bridges", [])
        
        logger.info(f"LLM Reasoning: {reasoning}")
        
        for bridge_data in bridges:
            # Find matching candidate
            matching = [
                c for c in original_candidates
                if c["type"] == bridge_data.get("type") and 
                   c["value"] == bridge_data.get("value")
            ]
            
            if matching:
                bridge = matching[0].copy()
                bridge["llm_confidence"] = bridge_data.get("confidence", 0.5)
                bridge["llm_rationale"] = bridge_data.get("rationale", "")
                ranked.append(bridge)
        
        # Add any candidates not ranked by LLM at the end
        ranked_values = {(b["type"], b["value"]) for b in ranked}
        for candidate in original_candidates:
            if (candidate["type"], candidate["value"]) not in ranked_values:
                candidate["llm_confidence"] = 0.3
                candidate["llm_rationale"] = "Not prioritized by LLM"
                ranked.append(candidate)
        
        return ranked
    
    def _static_ranking(self, candidates: List[Dict]) -> List[Dict]:
        """Fallback static ranking if LLM fails."""
        from .iterative_search import ENTITY_UNIQUENESS, rank_bridge_entities
        
        # Convert to ranking format
        tuples = [(c["type"], c["value"], ENTITY_UNIQUENESS.get(c["type"], 3)) 
                  for c in candidates]
        ranked_tuples = sorted(tuples, key=lambda x: x[2], reverse=True)
        
        # Convert back
        result = []
        for etype, evalue, score in ranked_tuples:
            result.append({
                "type": etype,
                "value": evalue,
                "llm_confidence": 0.5,
                "llm_rationale": "Static ranking fallback"
            })
        
        return result
```

### 2. LLM-Guided Iteration Decision

```python
class LLMGuidedIterativeSearch:
    """
    Iterative search with LLM-guided decision making at each step.
    """
    
    def __init__(
        self,
        processor: LogProcessor,
        llm_client: OllamaClient,
        prompt_builder: PromptBuilder,
        max_iterations: int = 5
    ):
        self.processor = processor
        self.bridge_selector = LLMGuidedBridgeSelector(llm_client, prompt_builder)
        self.max_iterations = max_iterations
        self.explored_entities = set()
        self.iteration_history = []
    
    def find_with_llm_guidance(
        self,
        logs: pd.DataFrame,
        query: str,
        target_entity_type: str,
        source_entity_value: str,
        source_entity_type: str = None
    ) -> Dict[str, Any]:
        """
        Iteratively search with LLM guiding bridge selection.
        """
        result = {
            "found": False,
            "target_values": [],
            "path": [],
            "iterations": 0,
            "reasoning_log": [],
            "confidence": 0.0
        }
        
        current_value = source_entity_value
        current_type = source_entity_type or "unknown"
        result["path"].append(f"{current_type}:{current_value}")
        
        # Iteration 1: Direct search
        logger.info(f"=== Iteration 1: Direct search ===")
        logger.info(f"Searching for {target_entity_type} in logs with {current_value}")
        
        source_logs = self._filter_logs_by_value(logs, current_value)
        direct_result = self._extract_target_from_logs(source_logs, target_entity_type)
        
        result["iterations"] = 1
        result["reasoning_log"].append({
            "iteration": 1,
            "action": "direct_search",
            "search_value": current_value,
            "logs_found": len(source_logs),
            "target_found": bool(direct_result)
        })
        
        if direct_result:
            result["found"] = True
            result["target_values"] = direct_result
            result["confidence"] = 1.0
            logger.info(f"✓ Found {target_entity_type} directly: {direct_result}")
            return result
        
        logger.info(f"✗ {target_entity_type} not found directly")
        
        # Extract bridge candidates
        logger.info("Extracting bridge entities from source logs...")
        all_entities = self._extract_all_entity_types(source_logs)
        bridge_candidates = self._format_as_candidates(all_entities)
        
        if not bridge_candidates:
            logger.warning("No bridge entities found")
            return result
        
        logger.info(f"Found {len(bridge_candidates)} potential bridges")
        
        # Iterative search with LLM guidance
        for iteration in range(2, self.max_iterations + 1):
            logger.info(f"\n=== Iteration {iteration}: LLM-guided bridge selection ===")
            
            result["iterations"] = iteration
            
            # Ask LLM to rank bridges
            ranked_bridges = self.bridge_selector.select_next_bridge(
                query=query,
                source_entity={"type": current_type, "value": current_value},
                target_entity_type=target_entity_type,
                bridge_candidates=bridge_candidates,
                context_logs=source_logs,
                iteration=iteration
            )
            
            if not ranked_bridges:
                logger.info("No more bridges to try")
                break
            
            # Try bridges in LLM-ranked order
            for bridge in ranked_bridges:
                if (bridge["type"], bridge["value"]) in self.explored_entities:
                    continue
                
                self.explored_entities.add((bridge["type"], bridge["value"]))
                
                logger.info(
                    f"\nTrying bridge: {bridge['type']}:{bridge['value']}\n"
                    f"  LLM Confidence: {bridge['llm_confidence']:.2f}\n"
                    f"  Rationale: {bridge['llm_rationale']}"
                )
                
                # Search via this bridge
                bridge_logs = self._filter_logs_by_value(logs, bridge["value"])
                
                result["reasoning_log"].append({
                    "iteration": iteration,
                    "action": "bridge_search",
                    "bridge": f"{bridge['type']}:{bridge['value']}",
                    "llm_confidence": bridge["llm_confidence"],
                    "llm_rationale": bridge["llm_rationale"],
                    "logs_found": len(bridge_logs)
                })
                
                if len(bridge_logs) == 0:
                    logger.info(f"  No logs found for {bridge['value']}, skipping")
                    continue
                
                # Try to find target
                bridge_result = self._extract_target_from_logs(bridge_logs, target_entity_type)
                
                if bridge_result:
                    result["found"] = True
                    result["target_values"] = bridge_result
                    result["path"].append(f"{bridge['type']}:{bridge['value']}")
                    result["path"].extend([f"{target_entity_type}:{v}" for v in bridge_result])
                    result["confidence"] = bridge["llm_confidence"] * 0.9  # Slightly reduced for indirect
                    
                    result["reasoning_log"][-1]["target_found"] = True
                    result["reasoning_log"][-1]["target_values"] = bridge_result
                    
                    logger.info(f"✓ SUCCESS! Found {target_entity_type}: {bridge_result}")
                    return result
                
                # Not found via this bridge, extract more entities for next iteration
                logger.info(f"  {target_entity_type} not found, extracting more bridges...")
                new_entities = self._extract_all_entity_types(bridge_logs)
                new_candidates = self._format_as_candidates(new_entities)
                
                # Add new candidates
                for new_cand in new_candidates:
                    if new_cand not in bridge_candidates:
                        bridge_candidates.append(new_cand)
                
                # Early exit if we've tried enough bridges this iteration
                if len([r for r in result["reasoning_log"] if r["iteration"] == iteration]) >= 3:
                    logger.info("Tried 3 bridges this iteration, moving to next iteration")
                    break
        
        logger.warning(f"Could not find {target_entity_type} after {result['iterations']} iterations")
        return result
    
    def _filter_logs_by_value(self, logs: pd.DataFrame, value: str) -> pd.DataFrame:
        """Search for value across all text columns."""
        mask = pd.Series([False] * len(logs), index=logs.index)
        
        for col in logs.select_dtypes(include=['object']).columns:
            mask |= logs[col].astype(str).str.contains(
                value, case=False, na=False, regex=False
            )
        
        return logs[mask]
    
    def _extract_target_from_logs(
        self, 
        logs: pd.DataFrame, 
        target_type: str
    ) -> List[str]:
        """Extract target entity from logs."""
        if len(logs) == 0:
            return []
        
        entities = self.processor.extract_entities(logs, target_type)
        return list(entities.keys()) if entities else []
    
    def _extract_all_entity_types(
        self, 
        logs: pd.DataFrame
    ) -> Dict[str, List[str]]:
        """Extract all entity types from logs."""
        from ..utils.config import config
        
        all_entities = {}
        entity_types = list(config.entity_mappings.get("patterns", {}).keys())
        
        for etype in entity_types:
            entities = self.processor.extract_entities(logs, etype)
            if entities:
                all_entities[etype] = list(entities.keys())
        
        return all_entities
    
    def _format_as_candidates(
        self, 
        entities: Dict[str, List[str]]
    ) -> List[Dict]:
        """Format entities as candidate dicts."""
        candidates = []
        for etype, values in entities.items():
            for value in values:
                candidates.append({"type": etype, "value": value})
        return candidates
```

### 3. Example Execution with LLM Reasoning

```python
Query: "find mdid for cm x"

═══════════════════════════════════════════════════════════
Iteration 1: Direct search
═══════════════════════════════════════════════════════════
Searching for mdid in logs with x
→ Found 3 logs containing "x"
→ Extracting mdid pattern from these logs
→ Result: NOT FOUND ✗

Extracting bridge entities from source logs...
Found 4 potential bridges:
  - rpdname: RPD001
  - dc_id: DC123
  - sf_id: SF456
  - ip_address: 192.168.1.1

═══════════════════════════════════════════════════════════
Iteration 2: LLM-guided bridge selection
═══════════════════════════════════════════════════════════
Asking LLM to reason about bridge selection...

LLM Reasoning:
"To find mdid (Modem ID), we need to understand the cable modem provisioning
architecture. The mdid is typically assigned and tracked at the RPD (Remote PHY
Device) level, as the RPD manages multiple modems and their configurations.

While IP address might seem relevant, it's assigned after provisioning and
doesn't directly map to modem ID assignment. DC (Downstream Channel) and SF
(Service Flow) are lower-level constructs that don't typically store modem IDs.

The RPD is the central management point that would log modem IDs during
registration and provisioning events."

LLM Ranked Bridges:
1. rpdname:RPD001
   Confidence: 0.92
   Rationale: "RPD manages modem provisioning and ID assignment"

2. ip_address:192.168.1.1
   Confidence: 0.65
   Rationale: "IP logs might contain modem references"

3. dc_id:DC123
   Confidence: 0.35
   Rationale: "Lower-level channel info, less likely to have mdid"

4. sf_id:SF456
   Confidence: 0.25
   Rationale: "Service flow is session-level, unlikely to contain mdid"

───────────────────────────────────────────────────────────
Trying bridge: rpdname:RPD001
  LLM Confidence: 0.92
  Rationale: RPD manages modem provisioning and ID assignment

Searching logs for "RPD001"...
→ Found 25 logs
→ Extracting mdid pattern from these logs
→ Result: FOUND! mdid = 98765 ✓

✓ SUCCESS! Found mdid: 98765

Final Result:
{
  "found": true,
  "target_values": ["98765"],
  "path": ["cm:x", "rpdname:RPD001", "mdid:98765"],
  "iterations": 2,
  "confidence": 0.83,  // 0.92 * 0.9
  "reasoning_log": [
    {
      "iteration": 1,
      "action": "direct_search",
      "target_found": false
    },
    {
      "iteration": 2,
      "action": "bridge_search",
      "bridge": "rpdname:RPD001",
      "llm_confidence": 0.92,
      "llm_rationale": "RPD manages modem provisioning and ID assignment",
      "target_found": true,
      "target_values": ["98765"]
    }
  ]
}
```

## Integration with LogAnalyzer

```python
class LogAnalyzer:
    def __init__(self, log_file_path: str):
        self.processor = LogProcessor(log_file_path)
        self.chunker = LogChunker()
        self.entity_manager = EntityManager()
        self.llm_client = OllamaClient()
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
        
        # LLM-guided iterative search
        self.llm_searcher = LLMGuidedIterativeSearch(
            processor=self.processor,
            llm_client=self.llm_client,
            prompt_builder=self.prompt_builder,
            max_iterations=5
        )
    
    def execute_relationship_search(self, parsed: Dict) -> Dict[str, Any]:
        """
        Execute relationship query with LLM-guided search.
        """
        target_type = parsed["primary_entity"]["type"]
        source_type = parsed["secondary_entity"]["type"]
        source_value = parsed["secondary_entity"]["value"]
        
        logs = self.processor.read_all_logs()
        
        # Use LLM-guided search
        result = self.llm_searcher.find_with_llm_guidance(
            logs=logs,
            query=parsed["original_query"],  # Pass original query for context
            target_entity_type=target_type,
            source_entity_value=source_value,
            source_entity_type=source_type
        )
        
        return {
            "query": parsed["original_query"],
            "source": {"type": source_type, "value": source_value},
            "target": {"type": target_type, "values": result["target_values"]},
            "found": result["found"],
            "search_path": result["path"],
            "iterations": result["iterations"],
            "confidence": result["confidence"],
            "reasoning_log": result["reasoning_log"],
            "summary": self._generate_llm_summary(result)
        }
```

## Benefits of LLM Reasoning

✅ **Intelligent Bridge Selection**
- Considers semantic relationships
- Uses domain knowledge
- Adapts to context

✅ **Faster Results**
- Tries best options first
- Avoids unlikely paths
- Reduces iterations

✅ **Explainable**
- Shows reasoning for each choice
- Provides confidence scores
- Transparent decision-making

✅ **Adaptive**
- Learns from log context
- Considers query intent
- Adjusts strategy dynamically

## Summary

**Before (Static):**
```
Bridge ranking: IP > RPD > SF > DC (fixed scores)
Try in order regardless of query or context
```

**After (LLM-Guided):**
```
Query: "find mdid for cm x"
LLM reasons: "mdid is provisioning data, RPD manages provisioning"
Bridge ranking: RPD > IP > DC > SF (contextual!)
Try RPD first → Success in iteration 2!
```

**Key Addition: LLM decides which bridge to try based on:**
1. Query intent (what are we looking for?)
2. Entity semantics (how are they related?)
3. Log context (what do the logs tell us?)
4. Domain knowledge (cable modem architecture)

Ready to implement! 🧠🚀

