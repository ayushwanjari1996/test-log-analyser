"""
Smart ReAct Orchestrator with Natural Language Interface.

Key differences from old orchestrator:
1. LLM outputs natural reasoning, not JSON
2. Tools parse and validate decisions
3. Zero hardcoded prompts
4. All context from configuration
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..llm.ollama_client import OllamaClient
from ..llm.dynamic_prompts import DynamicPromptBuilder
from ..utils.logger import setup_logger
from ..utils.exceptions import LLMError
from .tool_registry import ToolRegistry
from .tools.base_tool import ToolResult

logger = setup_logger()


@dataclass
class AnalysisResult:
    """Result of complete analysis"""
    success: bool
    answer: str
    confidence: float
    iterations: int
    tools_used: list
    reasoning_trace: list
    duration_seconds: float
    errors: list = field(default_factory=list)


class SmartOrchestrator:
    """
    Orchestrator that lets LLM reason naturally.
    
    No JSON formatting required from LLM.
    Tools handle all structuring and validation.
    """
    
    def __init__(self, llm_client: OllamaClient, tool_registry: ToolRegistry, max_iterations: int = 10):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.prompt_builder = DynamicPromptBuilder(tool_registry)
        self.max_iterations = max_iterations
        
        logger.info(f"SmartOrchestrator initialized with {len(tool_registry)} tools")
        logger.info("Using natural language interface - no JSON from LLM required")
    
    def execute(self, query: str) -> AnalysisResult:
        """Execute analysis with natural language ReAct loop"""
        
        start_time = datetime.now()
        logger.info("=" * 70)
        logger.info(f"SMART ORCHESTRATOR - Query: {query}")
        logger.info("=" * 70)
        
        # Build system prompt from config only
        system_prompt = self.prompt_builder.build_system_prompt()
        
        # State tracking
        iteration = 0
        decisions = []
        executions = []
        tools_used = []
        reasoning_trace = []
        errors = []
        cached_logs = None  # Track cached logs for auto-injection
        
        answer = None
        confidence = 0.0
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"\n{'─' * 70}")
            logger.info(f"📍 ITERATION {iteration}")
            logger.info(f"{'─' * 70}")
            
            # Build history from previous iterations
            history = self.prompt_builder.build_conversation_history(decisions, executions)
            
            # Build user prompt
            user_prompt = self.prompt_builder.build_user_prompt(query, iteration, history, has_cached_logs=(cached_logs is not None))
            
            # Get LLM response (natural language + tool call)
            logger.info("🤔 LLM is reasoning...")
            try:
                llm_response = self.llm_client.generate_json(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.3
                )
            except LLMError as e:
                logger.error(f"LLM error: {e}")
                errors.append(str(e))
                continue
            
            # LLM must output: tool name + parameters (simple structure)
            tool_name = llm_response.get("tool")
            parameters = llm_response.get("parameters", {})
            reasoning = llm_response.get("reasoning", "No reasoning provided")
            
            logger.info(f"💡 Reasoning: {reasoning[:150]}...")
            
            if not tool_name:
                logger.warning("LLM didn't specify tool")
                continue
            
            # Record decision
            decisions.append({
                "reasoning": reasoning,
                "tool_name": tool_name,
                "parameters": parameters
            })
            reasoning_trace.append({
                "reasoning": reasoning,
                "tool": tool_name
            })
            
            # Get and execute tool
            tool = self.tool_registry.get(tool_name)
            if not tool:
                error_msg = f"Unknown tool: {tool_name}"
                logger.error(error_msg)
                errors.append(error_msg)
                executions.append({"success": False, "error": error_msg})
                continue
            
            logger.info(f"🔧 Calling tool: {tool_name}")
            logger.info(f"📋 Parameters: {parameters}")
            
            # Auto-inject logs parameter if needed
            tools_needing_logs = ['extract_entities', 'count_entities', 'aggregate_entities', 
                                 'find_entity_relationships', 'filter_by_time', 'filter_by_severity', 
                                 'filter_by_field', 'fuzzy_search']
            
            if tool_name in tools_needing_logs and 'logs' not in parameters:
                if cached_logs is not None:
                    parameters['logs'] = cached_logs
                    logger.info(f"✓ Auto-injected cached logs ({len(cached_logs)} rows) into {tool_name}")
                else:
                    logger.warning(f"⚠ No cached logs available for {tool_name}. Call search_logs first.")
            
            # Special handling for finalize_answer
            if tool_name == "finalize_answer":
                result = tool.execute(**parameters)
                if result.success:
                    answer = result.data.get("answer")
                    confidence = result.data.get("confidence", 0.9)
                    logger.info(f"✅ Analysis finalized")
                    executions.append({"success": True, "message": "Finalized", "data": result.data})
                    tools_used.append(tool_name)
                    break
            
            # Validate parameters
            is_valid, error = tool.validate_parameters(parameters)
            if not is_valid:
                logger.error(f"Invalid parameters: {error}")
                executions.append({"success": False, "error": error})
                errors.append(error)
                continue
            
            # Execute tool
            try:
                result = tool.execute(**parameters)
                
                if result.success:
                    logger.info(f"✓ Tool succeeded: {result.message}")
                    executions.append({
                        "success": True,
                        "message": result.message,
                        "data": result.data
                    })
                    tools_used.append(tool_name)
                    
                    # Cache logs if this was a search
                    if tool_name == "search_logs" and result.data is not None:
                        # search_logs returns DataFrame directly as data, not wrapped in dict
                        import pandas as pd
                        if isinstance(result.data, pd.DataFrame):
                            cached_logs = result.data
                            logger.info(f"📦 Cached {len(cached_logs)} logs for subsequent tools")
                else:
                    logger.warning(f"✗ Tool failed: {result.error}")
                    executions.append({
                        "success": False,
                        "error": result.error
                    })
                    errors.append(result.error or "Tool execution failed")
                    
            except Exception as e:
                logger.error(f"Tool execution exception: {e}", exc_info=True)
                executions.append({"success": False, "error": str(e)})
                errors.append(str(e))
        
        # If didn't finalize explicitly, create default answer
        if not answer:
            answer = "Could not complete analysis within maximum iterations"
            confidence = 0.3
        
        duration = (datetime.now() - start_time).total_seconds()
        
        logger.info("=" * 70)
        logger.info("✅ ORCHESTRATION COMPLETE")
        logger.info(f"Iterations: {iteration}")
        logger.info(f"Success: {bool(answer)}")
        logger.info(f"Confidence: {confidence:.2f}")
        logger.info("=" * 70)
        
        return AnalysisResult(
            success=bool(answer) and confidence > 0.5,
            answer=answer,
            confidence=confidence,
            iterations=iteration,
            tools_used=tools_used,
            reasoning_trace=reasoning_trace,
            duration_seconds=duration,
            errors=errors
        )

