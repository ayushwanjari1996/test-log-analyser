"""
Hybrid Orchestrator - Main coordinator for the hybrid architecture
"""

from typing import Dict, Any, Optional
from .query_normalizer import QueryNormalizer
from .plan_executor import PlanExecutor
from .answer_formatter import AnswerFormatter
from .tool_registry import ToolRegistry
from .log_processor import LogProcessor
from .entity_manager import EntityManager
from .tools import create_all_tools
from ..llm.qwen_planner import QwenPlanner
from ..llm.ollama_client import OllamaClient
from ..utils.config import ConfigManager
from ..utils.logger import setup_logger

logger = setup_logger()


class HybridOrchestrator:
    """
    Main orchestrator for hybrid architecture.
    
    Flow:
    1. QueryNormalizer: Normalize entity aliases, extract search value
    2. QwenPlanner: Single LLM call → JSON plan
    3. PlanExecutor: Execute plan (search_logs hardcoded first)
    4. AnswerFormatter: Format results
    """
    
    def __init__(self, log_file: str, config_dir: str = "config", 
                 model: str = "qwen3-loganalyzer", verbose: bool = False):
        """
        Initialize orchestrator.
        
        Args:
            log_file: Path to log file (CSV)
            config_dir: Path to config directory
            model: LLM model name
            verbose: Enable verbose output
        """
        logger.info(f"Initializing HybridOrchestrator for {log_file}")
        
        self.verbose = verbose
        
        # Load config
        self.config = ConfigManager(config_dir)
        
        # Initialize components
        self.normalizer = QueryNormalizer(self.config)
        
        # LLM planner
        self.llm_client = OllamaClient(model=model)
        self.planner = QwenPlanner(self.llm_client, model=model)
        
        # Log processor and entity manager
        self.log_processor = LogProcessor(log_file)
        self.entity_manager = EntityManager()
        
        # Tool registry
        self.registry = ToolRegistry()
        tools = create_all_tools(log_file, config_dir)
        for tool in tools:
            self.registry.register(tool)
        
        # Executor and formatter
        self.executor = PlanExecutor(self.registry, self.log_processor)
        self.formatter = AnswerFormatter()
        
        logger.info(f"HybridOrchestrator ready with {len(tools)} tools")
    
    def process(self, query: str) -> Dict[str, Any]:
        """
        Process a user query.
        
        Args:
            query: Natural language query
            
        Returns:
            {
                "success": bool,
                "answer": str,
                "query": str,
                "normalized_query": str,
                "search_value": str,
                "plan": dict,
                "results": dict,
                "error": str (if any)
            }
        """
        logger.info("=" * 60)
        logger.info(f"Processing query: {query}")
        logger.info("=" * 60)
        
        try:
            # Step 1: Normalize query
            logger.info("Step 1: Normalizing query...")
            normalized = self.normalizer.normalize(query)
            
            normalized_query = normalized["normalized_query"]
            search_value = normalized["search_value"]
            detected_entities = normalized["detected_entities"]
            
            logger.info(f"  Normalized: {normalized_query}")
            logger.info(f"  Search value: {search_value or '(all logs)'}")
            logger.info(f"  Detected entities: {detected_entities}")
            
            # Step 2: Generate plan (single LLM call)
            logger.info("Step 2: Generating plan...")
            plan = self.planner.create_plan(normalized_query)
            
            logger.info(f"  Operations: {plan.get('operations', [])}")
            logger.info(f"  Params: {plan.get('params', {})}")
            
            # Step 3: Execute plan
            logger.info("Step 3: Executing plan...")
            results = self.executor.execute(search_value, plan)
            
            # Step 4: Format answer
            logger.info("Step 4: Formatting answer...")
            if self.verbose:
                answer = self.formatter.format_with_context(
                    results, query, normalized_query, search_value
                )
            else:
                answer = self.formatter.format(results, query)
            
            logger.info(f"Answer: {answer}")
            logger.info("=" * 60)
            
            return {
                "success": True,
                "answer": answer,
                "query": query,
                "normalized_query": normalized_query,
                "search_value": search_value,
                "detected_entities": detected_entities,
                "plan": plan,
                "results": {k: {"success": v.success, "message": v.message} 
                          for k, v in results.items()},
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "answer": f"Error: {str(e)}",
                "query": query,
                "error": str(e)
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

