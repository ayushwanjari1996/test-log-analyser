"""
Iterative ReAct Orchestrator.

Main orchestrator for iterative ReAct architecture where:
- LLM reasons and selects next tool (stateless, fresh prompt each iteration)
- Engine tracks state, executes tools, manages context (stateful)
- Context is curated (summaries, not full logs) to avoid overflow
"""

import json
import logging
import re
from typing import Dict, Any, Optional, Tuple
import pandas as pd

from .react_state import ReActState
from .context_builder import ContextBuilder
from .result_summarizer import ResultSummarizer
from .smart_summarizer import SmartSummarizer
from .tool_registry import ToolRegistry
from .tools import create_all_tools
from .tools.base_tool import ToolResult
from ..llm.ollama_client import OllamaClient
from ..utils.logger import setup_logger
from ..utils.exceptions import LLMError

logger = setup_logger()


class IterativeReactOrchestrator:
    """
    Iterative ReAct orchestrator.
    
    Implements a stateless LLM + stateful engine architecture:
    1. Build curated context (query + history + log summary)
    2. LLM decides next action (tool call or finalize)
    3. Execute tool with auto-injection of current logs
    4. Update state with results
    5. Repeat until done or max iterations
    
    Key features:
    - Smart context management (summaries, not full logs)
    - Tool auto-injection (logs passed automatically)
    - Entity tracking across iterations
    - Clear stop conditions
    """
    
    def __init__(
        self,
        log_file: str,
        config_dir: str = "config",
        model: str = "qwen3-react",
        max_iterations: int = 10,
        verbose: bool = False
    ):
        """
        Initialize orchestrator.
        
        Args:
            log_file: Path to log file (CSV)
            config_dir: Path to config directory
            model: LLM model name for reasoning
            max_iterations: Maximum iteration limit
            verbose: Enable verbose logging
        """
        logger.info(f"Initializing IterativeReactOrchestrator")
        logger.info(f"  Log file: {log_file}")
        logger.info(f"  Model: {model}")
        logger.info(f"  Max iterations: {max_iterations}")
        
        self.log_file = log_file
        self.config_dir = config_dir
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Initialize LLM
        self.llm_client = OllamaClient(model=model)
        logger.info(f"LLM client initialized: {model}")
        
        # Initialize tool registry
        self.registry = ToolRegistry()
        tools = create_all_tools(log_file, config_dir)
        for tool in tools:
            self.registry.register(tool)
        logger.info(f"Registered {len(tools)} tools")
        
        # Initialize context builder and summarizers
        self.context_builder = ContextBuilder(self.registry, max_history=5)
        self.summarizer = ResultSummarizer(max_text_length=100)
        self.smart_summarizer = SmartSummarizer(config_dir=config_dir, max_samples=10)
        
        logger.info("IterativeReactOrchestrator ready with SmartSummarizer")
    
    def process(self, query: str) -> Dict[str, Any]:
        """
        Process a query using iterative ReAct.
        
        Args:
            query: Natural language query
            
        Returns:
            Result dictionary with answer and metadata
        """
        print("\n" + "=" * 70)
        print(f"PROCESSING QUERY: {query}")
        print("=" * 70)
        
        # Initialize state
        state = ReActState(query, max_iterations=self.max_iterations)
        
        try:
            # Run iteration loop
            answer = self._run_iteration_loop(state)
            
            # Finalize state
            state.finalize(answer)
            
            # Build result
            result = {
                "success": True,
                "answer": answer,
                "query": query,
                "iterations": state.current_iteration,
                "max_iterations": state.max_iterations,
                "tools_used": [e.tool_name for e in state.tool_history],
                "summary": state.get_summary(),
                "error": None
            }
            
            print("\n" + "=" * 70)
            print(f"✓ SUCCESS")
            print(f"Answer: {answer}")
            print(f"Iterations: {state.current_iteration}/{state.max_iterations}")
            print("=" * 70)
            
            return result
            
        except Exception as e:
            print(f"\n✗ ERROR: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            
            state.finalize(f"Error: {str(e)}")
            
            return {
                "success": False,
                "answer": f"Error: {str(e)}",
                "query": query,
                "iterations": state.current_iteration,
                "error": str(e),
                "summary": state.get_summary()
            }
    
    def process_simple(self, query: str) -> str:
        """
        Simple interface - just returns the answer string.
        
        Args:
            query: Natural language query
            
        Returns:
            Answer string
        """
        result = self.process(query)
        return result["answer"]
    
    def _run_iteration_loop(self, state: ReActState) -> str:
        """
        Run the main iteration loop.
        
        Args:
            state: Current ReAct state
            
        Returns:
            Final answer string
        """
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        print(f"\nStarting iterative analysis (max {state.max_iterations} iterations)...")
        
        while state.current_iteration < state.max_iterations:
            state.increment_iteration()
            
            print(f"\n{'='*70}")
            print(f"ITERATION {state.current_iteration}/{state.max_iterations}")
            print(f"Query: {state.original_query}")
            print('='*70)
            
            try:
                # Step 1: Build context
                context = self.context_builder.build_context(state)
                
                # Step 2: Get LLM decision (now returns decision + raw response)
                decision, raw_response = self._get_llm_decision(context)
                
                # Display what we fed to LLM
                print(f"\n[What We Fed to LLM]")
                prompt = self.context_builder.build_prompt(context)
                print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
                
                # Display what LLM returned
                print(f"\n[What LLM Returned]")
                print(raw_response)
                
                # Display parsed decision
                print(f"\n[Parsed Decision]")
                print(f"  Reasoning: {decision.get('reasoning', 'N/A')}")
                print(f"  Action: {decision.get('action', 'N/A')}")
                print(f"  Params: {decision.get('params', {})}")
                
                # Reset failure counter on success
                consecutive_failures = 0
                
                # Step 3: Check if done
                if decision["action"] == "finalize_answer":
                    answer = decision.get("params", {}).get("answer", "No answer provided")
                    print(f"\n✓ FINAL ANSWER: {answer}")
                    print('='*70)
                    return answer
                
                # Step 4: Execute tool
                result = self._execute_tool(
                    decision["action"],
                    decision.get("params", {}),
                    state
                )
                
                # Display result
                print(f"\n[Tool Result]")
                if result.success:
                    print(f"  ✓ {result.message}")
                else:
                    print(f"  ✗ {result.error}")
                
                # Step 5: Update state
                self._update_state(state, decision, result)
                
            except LLMError as e:
                consecutive_failures += 1
                logger.error(f"LLM error (failure {consecutive_failures}/{max_consecutive_failures}): {e}")
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("Max consecutive failures reached, stopping")
                    return self._fallback_answer(state, f"LLM failed after {max_consecutive_failures} attempts: {e}")
                
            except Exception as e:
                logger.error(f"Iteration failed: {e}")
                import traceback
                traceback.print_exc()
                
                # Don't count as consecutive failure, just log and continue
                logger.warning("Continuing to next iteration despite error...")
        
        # Max iterations reached
        print(f"\n⚠️  Max iterations ({state.max_iterations}) reached")
        return self._fallback_answer(state, "Max iterations reached")
    
    def _get_llm_decision(self, context: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """
        Get LLM decision for next action.
        
        Args:
            context: Curated context from context_builder
            
        Returns:
            Decision dictionary with reasoning, action, and params
            
        Raises:
            LLMError: If LLM fails or returns invalid JSON
        """
        # Build prompt
        prompt = self.context_builder.build_prompt(context)
        
        if self.verbose:
            logger.debug(f"Prompt:\n{prompt[:500]}...")
        
        # Call LLM - DON'T use format_json since we have system prompt in Modelfile
        # The Modelfile already instructs the model to return JSON
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                format_json=False,  # Let Modelfile handle JSON instruction
                temperature=0.3
            )
            
            # Parse JSON
            decision = self._parse_llm_response(response)
            
            # Validate decision
            self._validate_decision(decision)
            
            # Return both decision and raw response
            return decision, response
            
        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            if 'response' in locals():
                logger.error(f"Response was: {response[:200]}...")
            raise LLMError(f"Failed to get LLM decision: {e}")
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response to extract JSON decision.
        
        Handles qwen3's <think> tags - extracts JSON AFTER the think tags.
        
        Args:
            response: Raw LLM response (may include <think>...</think> tags)
            
        Returns:
            Parsed decision dictionary
            
        Raises:
            LLMError: If parsing fails
        """
        if not response or len(response.strip()) == 0:
            raise LLMError("Empty response from LLM")
        
        # CRITICAL: Remove <think> tags first (qwen3 outputs these)
        # The JSON comes AFTER the think tags
        if '<think>' in response and '</think>' in response:
            logger.debug("Detected <think> tags, extracting content after them")
            # Split on </think> and take everything after
            parts = response.split('</think>')
            if len(parts) > 1:
                response = parts[-1].strip()  # Take content after last </think>
                logger.debug(f"Extracted content after think tags: {response[:100]}...")
        
        # Strategy 1: Try direct JSON parse
        try:
            parsed = json.loads(response)
            logger.debug("Direct JSON parse successful")
            return parsed
        except json.JSONDecodeError as e:
            logger.debug(f"Direct parse failed: {e}")
            pass
        
        # Strategy 2: Extract JSON from markdown code blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        if matches:
            try:
                parsed = json.loads(matches[0])
                logger.debug("Markdown block JSON parse successful")
                return parsed
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find first { to last } (most permissive)
        try:
            start = response.index('{')
            end = response.rindex('}') + 1
            json_str = response[start:end]
            
            # Try to clean up common issues
            json_str = json_str.strip()
            
            # Remove trailing commas before } or ]
            json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
            
            parsed = json.loads(json_str)
            logger.debug("Extracted JSON parse successful")
            return parsed
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug(f"JSON extraction failed: {e}")
            pass
        
        # If all else fails, show what we got
        raise LLMError(
            f"Could not parse JSON from LLM response.\n"
            f"Response length: {len(response)} chars\n"
            f"First 500 chars: {response[:500]}\n"
            f"Last 200 chars: {response[-200:]}"
        )
    
    def _validate_decision(self, decision: Dict[str, Any]) -> None:
        """
        Validate LLM decision.
        
        Args:
            decision: Decision dictionary
            
        Raises:
            LLMError: If decision is invalid
        """
        if "action" not in decision:
            raise LLMError("Decision missing 'action' field")
        
        action = decision["action"]
        
        # Check if action is finalize_answer
        if action == "finalize_answer":
            if "params" not in decision or "answer" not in decision.get("params", {}):
                raise LLMError("finalize_answer requires 'answer' in params")
            return
        
        # Check if tool exists
        if action not in self.registry:
            available = ", ".join(self.registry.list_tools())
            raise LLMError(f"Unknown tool '{action}'. Available: {available}")
    
    def _execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        state: ReActState
    ) -> ToolResult:
        """
        Execute a tool with auto-injection.
        
        Args:
            tool_name: Name of tool to execute
            params: Tool parameters
            state: Current state (for auto-injection)
            
        Returns:
            ToolResult object
        """
        tool = self.registry.get(tool_name)
        
        if tool is None:
            error_msg = f"Tool '{tool_name}' not found in registry"
            logger.error(error_msg)
            return ToolResult(
                success=False,
                data=None,
                message=error_msg,
                error=error_msg
            )
        
        # Auto-inject logs if tool needs them
        if hasattr(tool, 'requires_logs') and tool.requires_logs:
            if state.current_logs is not None:
                if self.verbose:
                    logger.debug(f"  Auto-injecting logs: {len(state.current_logs)} rows")
                params["logs"] = state.current_logs
            else:
                if self.verbose:
                    logger.warning(f"  Tool requires logs but none are loaded")
        
        # Execute tool
        try:
            result = tool.execute(**params)
            return result
            
        except Exception as e:
            error_msg = f"Tool execution failed: {e}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            
            return ToolResult(
                success=False,
                data=None,
                message=error_msg,
                error=str(e)
            )
    
    def _update_state(
        self,
        state: ReActState,
        decision: Dict[str, Any],
        result: ToolResult
    ) -> None:
        """
        Update state after tool execution.
        
        Args:
            state: Current state
            decision: LLM decision
            result: Tool execution result
        """
        tool_name = decision["action"]
        params = decision.get("params", {})
        
        # Record tool execution
        state.add_tool_execution(
            tool_name=tool_name,
            parameters=params,
            result=result,
            success=result.success,
            error=result.error if not result.success else None
        )
        
        # Update current logs if tool returned logs
        if result.success and result.data is not None:
            if isinstance(result.data, pd.DataFrame) and not result.data.empty:
                if self.verbose:
                    logger.debug(f"  Updating current_logs: {len(result.data)} rows")
                
                # Use SmartSummarizer for large datasets
                if len(result.data) > 50:
                    summary_result = self.smart_summarizer.summarize(result.data)
                    state.update_current_logs(result.data, summary=summary_result['summary_text'])
                    
                    if self.verbose:
                        logger.debug(f"  Smart summary generated: {len(summary_result['summary_text'])} chars")
                else:
                    # Small datasets: store as-is
                    state.update_current_logs(result.data)
            
            # Update entities if extracted
            elif isinstance(result.data, dict) and all(isinstance(v, list) for v in result.data.values()):
                if self.verbose:
                    logger.debug(f"  Updating entities: {list(result.data.keys())}")
                state.update_entities(result.data)
    
    def _fallback_answer(self, state: ReActState, reason: str) -> str:
        """
        Generate fallback answer when loop doesn't complete normally.
        
        Args:
            state: Current state
            reason: Reason for fallback
            
        Returns:
            Fallback answer string
        """
        logger.warning(f"Generating fallback answer: {reason}")
        
        # Try to provide useful information based on what we have
        if state.current_logs is not None:
            log_count = len(state.current_logs)
            answer = f"Analysis incomplete ({reason}). Found {log_count} logs."
            
            if state.extracted_entities:
                entity_summary = ", ".join([
                    f"{k}: {len(v)}" for k, v in state.extracted_entities.items()
                ])
                answer += f" Extracted entities: {entity_summary}."
        else:
            answer = f"Analysis incomplete ({reason}). No data available."
        
        return answer

