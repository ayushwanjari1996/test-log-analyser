"""
Workflow Orchestrator - The main engine for intelligent analysis workflows.

This module orchestrates multi-step analysis by calling methods based on
LLM decisions, tracking context, and iterating until the query is answered.
"""

import logging
from typing import Dict
from dataclasses import dataclass, field

from .analysis_context import AnalysisContext
from .decision_agent import LLMDecisionAgent
from .methods import (
    DirectSearchMethod,
    IterativeSearchMethod,
    PatternAnalysisMethod,
    TimelineAnalysisMethod,
    RootCauseAnalysisMethod,
    SummarizationMethod,
    RelationshipMappingMethod
)
from ..core.log_processor import LogProcessor
from ..core.entity_manager import EntityManager
from ..llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Comprehensive result from workflow orchestrator."""
    success: bool
    answer: str
    confidence: float
    logs_analyzed: int
    entities_found: Dict
    errors_found: list
    patterns: list = field(default_factory=list)
    timeline: list = field(default_factory=list)
    causal_chain: list = field(default_factory=list)
    execution_trace: list = field(default_factory=list)
    iterations: int = 0
    summary: Dict = field(default_factory=dict)
    methods_used: list = field(default_factory=list)


class WorkflowOrchestrator:
    """
    Orchestrates multi-step analysis workflow.
    
    This is the main engine that:
    1. Initializes analysis context
    2. Loops: Ask LLM → Execute method → Update context
    3. Continues until answer found or max iterations
    4. Returns comprehensive results
    """
    
    def __init__(
        self,
        processor: LogProcessor,
        entity_manager: EntityManager,
        llm_client: OllamaClient
    ):
        self.processor = processor
        self.entity_manager = entity_manager
        self.llm_client = llm_client
        
        # Initialize decision agent
        self.decision_agent = LLMDecisionAgent(
            llm_client=llm_client,
            max_iterations=10
        )
        
        # Initialize all analysis methods
        self.methods = {
            "direct_search": DirectSearchMethod(processor, entity_manager),
            "iterative_search": IterativeSearchMethod(processor, entity_manager, llm_client),
            "pattern_analysis": PatternAnalysisMethod(llm_client),
            "timeline_analysis": TimelineAnalysisMethod(llm_client),
            "root_cause_analysis": RootCauseAnalysisMethod(llm_client),
            "summarization": SummarizationMethod(llm_client),
            "relationship_mapping": RelationshipMappingMethod(entity_manager)
        }
        
        logger.info("WorkflowOrchestrator initialized with 7 analysis methods")
    
    def execute(self, query: str, parsed_query: Dict) -> AnalysisResult:
        """
        Execute intelligent analysis workflow.
        
        Args:
            query: Original user query
            parsed_query: Parsed query from LLMQueryParser
            
        Returns:
            AnalysisResult with comprehensive findings
        """
        
        logger.info(f"\n{'='*70}")
        logger.info(f"INTELLIGENT WORKFLOW ORCHESTRATOR")
        logger.info(f"Query: {query}")
        logger.info(f"{'='*70}\n")
        
        # Step 1: Initialize context
        context = self._initialize_context(query, parsed_query)
        
        # Step 2: Iterative execution loop
        while context.iteration < self.decision_agent.max_iterations:
            
            # Check if we're going in circles
            if context.is_going_in_circles():
                logger.warning("⚠ Circular reasoning detected!")
            
            # Ask LLM: What should we do next?
            decision = self.decision_agent.decide_next_step(
                query_intent=context.query_intent,
                current_context=context,
                iteration=context.iteration
            )
            
            logger.info(f"\n{'─'*60}")
            logger.info(f"📍 ITERATION {context.iteration + 1}")
            logger.info(f"Method: {decision.method}")
            logger.info(f"Reasoning: {decision.reasoning}")
            logger.info(f"Confidence: {decision.confidence:.2f}")
            logger.info(f"{'─'*60}")
            
            # Execute the chosen method
            result = self._execute_method(decision.method, decision.params, context)
            
            # Check for critical errors - terminate immediately
            if "error" in result and result.get("critical", False):
                logger.error(f"💥 Critical error encountered: {result['error']}")
                logger.info("Terminating workflow due to critical error")
                break
            
            # Update context with results
            self._update_context(context, decision, result)
            
            # Check success criteria
            if self._check_success(context, parsed_query):
                logger.info("✓ Success criteria met!")
                context.answer_found = True
                decision.should_stop = True
            
            # Should we stop?
            if decision.should_stop:
                logger.info(f"🛑 Stopping: {decision.reasoning}")
                break
        
        # Step 3: Final summarization if not already done
        if not context.has_tried("summarization"):
            logger.info("\n📝 Creating final summary...")
            summary_result = self.methods["summarization"].execute({}, context)
            context.add_step("summarization", {}, summary_result, "Final summary")
        else:
            # Get summary from last summarization step
            summary_result = next(
                (step.result for step in reversed(context.step_history) 
                 if step.method == "summarization"),
                {}
            )
        
        # Step 4: Build and return result
        return self._build_final_result(context, summary_result)
    
    def _initialize_context(self, query: str, parsed: Dict) -> AnalysisContext:
        """Initialize analysis context from parsed query."""
        
        # Determine intent
        query_type = parsed.get("query_type", "find")
        intent_map = {
            "specific_value": "find",
            "relationship": "find",
            "aggregation": "analyze",
            "analysis": "root_cause"
        }
        intent = intent_map.get(query_type, "find")
        
        # Extract target entity
        primary = parsed.get("primary_entity", {})
        secondary = parsed.get("secondary_entity", {})
        
        # For relationship queries: "find X for Y z"
        # - PRIMARY (X) = what we're LOOKING FOR (target type)
        # - SECONDARY (Y z) = what we START FROM (search value)
        if query_type == "relationship" and secondary and secondary.get("value"):
            # We're searching FOR primary type, STARTING FROM secondary value
            target_value = secondary["value"]  # Start from this value
            target_type = primary.get("type")  # Looking for this type
        elif primary:
            target_value = primary.get("value", "")
            target_type = primary.get("type")
        else:
            target_value = ""
            target_type = None
        
        # Build goal and success criteria
        goal = f"Answer query: {query}"
        if "why" in query.lower() or "fail" in query.lower() or "offline" in query.lower():
            success_criteria = "Found root cause of the issue"
        elif "analyse" in query.lower() or "analyze" in query.lower():
            success_criteria = "Provided comprehensive analysis of logs"
        else:
            success_criteria = "Found relevant logs and entities"
        
        context = AnalysisContext(
            original_query=query,
            query_intent=intent,
            goal=goal,
            success_criteria=success_criteria,
            target_entity=target_value,
            target_entity_type=target_type
        )
        
        logger.info(f"Context initialized:")
        logger.info(f"  Intent: {intent}")
        logger.info(f"  Target: {target_type}:{target_value}")
        logger.info(f"  Goal: {goal}")
        
        return context
    
    def _execute_method(self, method_name: str, params: Dict, context: AnalysisContext) -> Dict:
        """Execute a specific analysis method."""
        
        if method_name not in self.methods:
            logger.error(f"❌ Unknown method: {method_name}")
            return {"error": f"Unknown method: {method_name}"}
        
        method = self.methods[method_name]
        
        try:
            logger.info(f"⚙️  Executing {method_name}...")
            result = method.execute(params, context)
            
            # Log summary of results
            logs_found = len(result.get("logs", []))
            entities_found = sum(len(v) for v in result.get("entities", {}).values())
            errors_found = len(result.get("errors", []))
            
            logger.info(f"✓ {method_name} completed:")
            logger.info(f"  Logs: {logs_found}, Entities: {entities_found}, Errors: {errors_found}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Method {method_name} failed: {e}", exc_info=True)
            
            # Determine if this is a critical error that should stop the workflow
            critical_errors = [
                "ModuleNotFoundError",
                "ImportError", 
                "NameError",
                "SyntaxError",
                "AttributeError"  # Usually indicates code issue
            ]
            
            is_critical = any(err in str(type(e).__name__) for err in critical_errors)
            
            if is_critical:
                logger.error(f"⚠️  Critical error detected: {type(e).__name__}")
                return {"error": str(e), "critical": True}
            else:
                # Non-critical error - workflow can continue
                logger.warning(f"Non-critical error - workflow will attempt to continue")
                return {"error": str(e), "critical": False}
    
    def _update_context(self, context: AnalysisContext, decision, result: Dict):
        """Update context with method results."""
        
        # Record the step
        context.add_step(
            method=decision.method,
            params=decision.params,
            result=result,
            reasoning=decision.reasoning
        )
        
        # Add any new logs found
        if "logs" in result and result["logs"]:
            context.add_logs(result["logs"])
        
        # Add any entities discovered with priorities
        if "entities" in result and result["entities"]:
            for entity_type, values in result["entities"].items():
                for value in values:
                    # Get priority based on entity type and query
                    priority = self.decision_agent.get_entity_priority(
                        entity_type=entity_type,
                        intent=context.query_intent,
                        query=context.original_query
                    )
                    context.add_entity(entity_type, value, priority)
        
        # Add errors
        if "errors" in result and result["errors"]:
            context.errors_found.extend(result["errors"])
        
        # Add patterns
        if "patterns" in result and result["patterns"]:
            context.patterns.extend(result["patterns"])
        
        # Add relationships
        if "relationships" in result and result["relationships"]:
            context.relationships.extend(result["relationships"])
        
        # Update answer if found
        if "answer" in result and result.get("answer"):
            context.answer = result["answer"]
            context.confidence = result.get("confidence", 0.8)
            context.answer_found = True
    
    def _check_success(self, context: AnalysisContext, parsed: Dict) -> bool:
        """Check if success criteria met based on query intent."""
        
        query_lower = context.original_query.lower()
        
        # For root cause queries - need to find errors or have an answer
        if any(kw in query_lower for kw in ["why", "fail", "offline", "error", "crash"]):
            return len(context.errors_found) > 0 or context.answer_found
        
        # For analysis queries - need logs and some analysis done
        if any(kw in query_lower for kw in ["analyse", "analyze", "what happened", "timeline"]):
            return context.logs_analyzed > 0 and (
                len(context.patterns) > 0 or 
                context.has_tried("timeline_analysis") or
                context.has_tried("root_cause_analysis") or
                context.iteration >= 2  # At least 2 iterations of analysis
            )
        
        # For specific value queries - finding logs is enough
        if parsed.get("query_type") == "specific_value":
            return context.logs_analyzed > 0
        
        # For relationship queries - need to find the TARGET entity type
        if parsed.get("query_type") == "relationship":
            # Get what entity type user is looking for (primary entity)
            primary = parsed.get("primary_entity", {})
            target_type = primary.get("type")
            
            # Check if we found entities of that type
            if target_type and target_type in context.entities:
                logger.info(f"✓ Found target entity type '{target_type}': {context.entities[target_type]}")
                return True
            
            # If we found logs but not the target entity, keep searching
            # Only stop if we've tried iterative search or exhausted options
            if context.has_tried("iterative_search") and context.iteration >= 3:
                return True  # Tried hard enough, accept what we have
            
            return False  # Keep searching!
        
        # Generic: have we found something useful?
        return context.logs_analyzed > 0 or context.answer_found
    
    def _build_final_result(self, context: AnalysisContext, summary: Dict) -> AnalysisResult:
        """Build comprehensive final result."""
        
        # Build execution trace
        execution_trace = []
        for step in context.step_history:
            execution_trace.append({
                "iteration": step.iteration,
                "method": step.method,
                "reasoning": step.reasoning,
                "logs_found": len(step.result.get("logs", [])),
                "entities_found": sum(len(v) for v in step.result.get("entities", {}).values()),
                "errors_found": len(step.result.get("errors", [])),
                "timestamp": step.timestamp.isoformat()
            })
        
        # Determine success
        success = context.answer_found or context.logs_analyzed > 0
        
        # Build answer
        if context.answer:
            answer = context.answer
        elif summary.get("summary"):
            answer = summary["summary"]
        elif context.logs_analyzed > 0:
            answer = f"Found {context.logs_analyzed} logs" + (
                f" with {len(context.errors_found)} errors" if context.errors_found else ""
            )
        else:
            answer = "No logs found for this query"
        
        result = AnalysisResult(
            success=success,
            answer=answer,
            confidence=context.confidence or summary.get("confidence", 0.7),
            logs_analyzed=context.logs_analyzed,
            entities_found=context.entities,
            errors_found=context.errors_found,
            patterns=context.patterns,
            timeline=summary.get("timeline", []),
            causal_chain=summary.get("causal_chain", []),
            execution_trace=execution_trace,
            iterations=context.iteration,
            summary=summary,
            methods_used=list(context.methods_tried)
        )
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ WORKFLOW COMPLETE")
        logger.info(f"Success: {result.success}")
        logger.info(f"Iterations: {result.iterations}")
        logger.info(f"Logs analyzed: {result.logs_analyzed}")
        logger.info(f"Methods used: {', '.join(result.methods_used)}")
        logger.info(f"{'='*70}\n")
        
        return result

