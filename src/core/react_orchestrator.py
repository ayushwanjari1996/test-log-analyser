"""
ReAct Orchestrator - Main engine for intelligent log analysis.

Implements the ReAct (Reason + Act) pattern where the LLM:
1. Reasons about what to do next
2. Acts by calling a tool
3. Observes the result
4. Repeats until the query is answered

This replaces the rigid method-centric workflow with flexible tool composition.
"""

import logging
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .react_state import ReActState
from .tool_registry import ToolRegistry
from ..llm.ollama_client import OllamaClient
from ..llm.react_prompts import ReActPromptBuilder
from .tools.base_tool import ToolResult
from ..utils.exceptions import LLMError

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Final result from ReAct analysis"""
    success: bool
    answer: str
    confidence: float
    query: str
    iterations: int
    tools_used: list
    reasoning_trace: list
    duration_seconds: float
    metadata: Dict[str, Any]


class ReActOrchestrator:
    """
    Main orchestrator implementing ReAct pattern.
    
    The LLM is in full control:
    - Decides which tool to use
    - Decides parameters
    - Decides when to stop
    - Adapts strategy based on observations
    
    The code just provides tools and executes them.
    """
    
    def __init__(
        self,
        llm_client: OllamaClient,
        tool_registry: ToolRegistry,
        max_iterations: int = 10,
        config_dir: str = "config"
    ):
        """
        Initialize ReAct orchestrator.
        
        Args:
            llm_client: LLM client for reasoning
            tool_registry: Registry of available tools
            max_iterations: Maximum reasoning iterations
            config_dir: Path to configuration directory
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.prompt_builder = ReActPromptBuilder(config_dir)
        
        logger.info(f"ReActOrchestrator initialized with {len(tool_registry)} tools")
    
    def execute(self, query: str) -> AnalysisResult:
        """
        Execute ReAct loop to answer user query.
        
        Args:
            query: User's natural language question
            
        Returns:
            AnalysisResult with answer and execution trace
        """
        logger.info("="*70)
        logger.info(f"REACT ORCHESTRATOR - Query: {query}")
        logger.info("="*70)
        
        # Initialize state
        state = ReActState(query, max_iterations=self.max_iterations)
        
        # Build system prompt (with tool descriptions)
        tool_descriptions = self.tool_registry.get_tools_description()
        system_prompt = self.prompt_builder.build_system_prompt(tool_descriptions)
        
        # Main ReAct loop
        while not state.done and not state.is_max_iterations_reached():
            logger.info(f"\n{'─'*70}")
            logger.info(f"📍 ITERATION {state.current_iteration + 1}")
            logger.info(f"{'─'*70}")
            
            try:
                # Get conversation history
                history = state.get_conversation_history()
                
                # Build user prompt
                user_prompt = self.prompt_builder.build_user_prompt(
                    query=query,
                    iteration=state.current_iteration,
                    conversation_history=history
                )
                
                # Ask LLM: What should we do?
                logger.info("🤔 LLM is reasoning...")
                llm_response = self.llm_client.generate_json(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.3
                )
                
                # Parse LLM decision
                decision = self._parse_llm_decision(llm_response)
                
                # Log decision
                logger.info(f"💡 Reasoning: {decision['reasoning'][:100]}...")
                
                if decision['done']:
                    # LLM says we're done
                    logger.info(f"✅ LLM concluded: {decision['answer'][:100]}...")
                    state.add_llm_decision(
                        reasoning=decision['reasoning'],
                        tool_name=None,
                        parameters={},
                        answer=decision['answer'],
                        confidence=decision['confidence'],
                        done=True
                    )
                    state.finalize(decision['answer'], decision['confidence'])
                    break
                
                # LLM wants to call a tool
                tool_name = decision['tool']
                parameters = decision['parameters']
                
                if not tool_name:
                    logger.warning("LLM didn't specify a tool, asking again...")
                    state.increment_iteration()
                    continue
                
                logger.info(f"🔧 Calling tool: {tool_name}")
                logger.info(f"📋 Parameters: {parameters}")
                
                # Record LLM decision
                state.add_llm_decision(
                    reasoning=decision['reasoning'],
                    tool_name=tool_name,
                    parameters=parameters,
                    done=False
                )
                
                # Execute tool
                tool_result = self._execute_tool(tool_name, parameters, state)
                
                # Record tool execution
                state.add_tool_execution(
                    tool_name=tool_name,
                    parameters=parameters,
                    result=tool_result,
                    success=tool_result.success if isinstance(tool_result, ToolResult) else True,
                    error=tool_result.error if isinstance(tool_result, ToolResult) else None
                )
                
                # Cache results for tool chaining
                if isinstance(tool_result, ToolResult) and tool_result.success:
                    # Store logs if this was a search
                    if tool_name == "search_logs" and hasattr(tool_result, 'data'):
                        state.filtered_logs = tool_result.data
                        logger.info(f"Cached search results: {len(tool_result.data)} logs available for next tools")
                
                # Log result
                if isinstance(tool_result, ToolResult):
                    if tool_result.success:
                        logger.info(f"✓ Tool succeeded: {tool_result.message}")
                    else:
                        logger.warning(f"✗ Tool failed: {tool_result.error}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM JSON: {e}")
                state.increment_iteration()
                continue
            
            except LLMError as e:
                logger.error(f"LLM error: {e}")
                # LLM returned invalid JSON - try to continue
                state.increment_iteration()
                continue
            
            except Exception as e:
                logger.error(f"Error in ReAct loop: {e}", exc_info=True)
                state.increment_iteration()
                continue
            
            # Move to next iteration
            state.increment_iteration()
        
        # Check why we stopped
        if state.is_max_iterations_reached() and not state.done:
            logger.warning("⚠ Max iterations reached without conclusive answer")
            state.finalize(
                answer="Could not find a conclusive answer after maximum iterations. Please try rephrasing your question.",
                confidence=0.3
            )
        
        # Build final result
        result = self._build_result(state)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ REACT COMPLETE")
        logger.info(f"Iterations: {result.iterations}")
        logger.info(f"Success: {result.success}")
        logger.info(f"Confidence: {result.confidence:.2f}")
        logger.info(f"{'='*70}\n")
        
        return result
    
    def _parse_llm_decision(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse LLM's JSON response into decision.
        
        Expected format:
        {
          "reasoning": "...",
          "tool": "tool_name" or null,
          "parameters": {...},
          "answer": "..." or null,
          "confidence": 0.0-1.0,
          "done": true/false
        }
        """
        return {
            "reasoning": llm_response.get("reasoning", "No reasoning provided"),
            "tool": llm_response.get("tool"),
            "parameters": llm_response.get("parameters", {}),
            "answer": llm_response.get("answer"),
            "confidence": llm_response.get("confidence", 0.5),
            "done": llm_response.get("done", False)
        }
    
    def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], state) -> ToolResult:
        """
        Execute a tool with given parameters.
        
        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters
            state: Current ReActState for accessing cached data
            
        Returns:
            ToolResult from tool execution
        """
        # Get tool
        tool = self.tool_registry.get(tool_name)
        if not tool:
            error_msg = f"Tool '{tool_name}' not found in registry"
            logger.error(error_msg)
            return ToolResult(
                success=False,
                data=None,
                error=error_msg
            )
        
        # Auto-inject logs from state if tool needs them and LLM didn't provide
        if 'logs' in [p.name for p in tool.parameters]:
            if parameters.get('logs') is None or isinstance(parameters.get('logs'), str):
                # LLM didn't provide valid logs, use cached if available
                if state.filtered_logs is not None and not state.filtered_logs.empty:
                    logger.info(f"Auto-injecting cached logs ({len(state.filtered_logs)} rows) into {tool_name}")
                    parameters['logs'] = state.filtered_logs
                elif state.loaded_logs is not None and not state.loaded_logs.empty:
                    logger.info(f"Auto-injecting all logs ({len(state.loaded_logs)} rows) into {tool_name}")
                    parameters['logs'] = state.loaded_logs
        
        # Validate parameters
        valid, error = tool.validate_parameters(parameters)
        if not valid:
            logger.error(f"Invalid parameters: {error}")
            return ToolResult(
                success=False,
                data=None,
                error=f"Invalid parameters: {error}"
            )
        
        # Execute tool
        try:
            result = tool.execute(**parameters)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
    
    def _build_result(self, state: ReActState) -> AnalysisResult:
        """Build final AnalysisResult from state"""
        summary = state.get_summary()
        
        return AnalysisResult(
            success=state.done,
            answer=state.answer or "No answer generated",
            confidence=state.confidence,
            query=state.original_query,
            iterations=state.current_iteration,
            tools_used=summary["tool_sequence"],
            reasoning_trace=[d.to_dict() for d in state.llm_decisions],
            duration_seconds=summary["duration_seconds"] or 0.0,
            metadata={
                "max_iterations_reached": state.is_max_iterations_reached(),
                "tool_executions": len(state.tool_history)
            }
        )

