"""Prompt building and template management for LLM interactions."""

from typing import Dict, Any, Optional, List
from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger()


class PromptBuilder:
    """
    Builds prompts for different analysis modes using templates from config.
    """
    
    def __init__(self):
        """Initialize prompt builder with templates from config."""
        self.prompts = config.prompts
        logger.info("Initialized PromptBuilder")
    
    def build_find_prompt(
        self,
        entity: str,
        log_chunk: str,
        additional_context: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Build prompt for FIND mode.
        
        Args:
            entity: Entity to search for
            log_chunk: Log data chunk
            additional_context: Optional additional context
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        find_config = self.prompts.get('find_mode', {})
        
        system_prompt = find_config.get('system', '')
        user_template = find_config.get('user_template', '')
        
        user_prompt = user_template.format(
            entity=entity,
            log_chunk=log_chunk
        )
        
        if additional_context:
            user_prompt += f"\n\nAdditional context: {additional_context}"
        
        logger.debug(f"Built FIND prompt for entity '{entity}' ({len(log_chunk)} chars)")
        return system_prompt, user_prompt
    
    def build_analyze_prompt(
        self,
        user_query: str,
        log_chunk: str,
        focus_entities: Optional[List[str]] = None,
        additional_context: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Build prompt for ANALYZE mode.
        
        Args:
            user_query: User's analysis question
            log_chunk: Log data chunk
            focus_entities: Entities to focus analysis on
            additional_context: Optional additional context
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        analyze_config = self.prompts.get('analyze_mode', {})
        
        system_prompt = analyze_config.get('system', '')
        user_template = analyze_config.get('user_template', '')
        
        focus_str = ', '.join(focus_entities) if focus_entities else 'all entities'
        
        user_prompt = user_template.format(
            user_query=user_query,
            log_chunk=log_chunk,
            focus_entities=focus_str
        )
        
        if additional_context:
            user_prompt += f"\n\nAdditional context: {additional_context}"
        
        logger.debug(f"Built ANALYZE prompt for query '{user_query}' ({len(log_chunk)} chars)")
        return system_prompt, user_prompt
    
    def build_trace_prompt(
        self,
        entity: str,
        log_chunk: str,
        additional_context: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Build prompt for TRACE mode.
        
        Args:
            entity: Entity to trace
            log_chunk: Log data chunk
            additional_context: Optional additional context
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        trace_config = self.prompts.get('trace_mode', {})
        
        system_prompt = trace_config.get('system', '')
        user_template = trace_config.get('user_template', '')
        
        user_prompt = user_template.format(
            entity=entity,
            log_chunk=log_chunk
        )
        
        if additional_context:
            user_prompt += f"\n\nAdditional context: {additional_context}"
        
        logger.debug(f"Built TRACE prompt for entity '{entity}' ({len(log_chunk)} chars)")
        return system_prompt, user_prompt
    
    def build_custom_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """
        Build custom prompt with variable substitution.
        
        Args:
            system_prompt: System prompt template
            user_prompt: User prompt template
            variables: Dictionary of variables to substitute
            
        Returns:
            Tuple of (formatted_system_prompt, formatted_user_prompt)
        """
        if variables:
            try:
                system_prompt = system_prompt.format(**variables)
                user_prompt = user_prompt.format(**variables)
            except KeyError as e:
                logger.warning(f"Missing variable in prompt template: {e}")
        
        logger.debug("Built custom prompt")
        return system_prompt, user_prompt
    
    def estimate_prompt_tokens(self, prompt: str) -> int:
        """
        Estimate token count for a prompt.
        Rough estimate: ~4 characters per token.
        
        Args:
            prompt: Prompt text
            
        Returns:
            Estimated token count
        """
        return len(prompt) // 4
    
    def truncate_log_chunk(
        self,
        log_chunk: str,
        max_tokens: int = 3000
    ) -> str:
        """
        Truncate log chunk to fit within token limit.
        
        Args:
            log_chunk: Log data to truncate
            max_tokens: Maximum tokens allowed
            
        Returns:
            Truncated log chunk
        """
        max_chars = max_tokens * 4
        
        if len(log_chunk) <= max_chars:
            return log_chunk
        
        # Truncate and add indicator
        truncated = log_chunk[:max_chars]
        lines = truncated.split('\n')
        
        # Remove partial last line
        if len(lines) > 1:
            truncated = '\n'.join(lines[:-1])
        
        truncated += f"\n... [truncated, {len(log_chunk) - len(truncated)} chars omitted]"
        
        logger.warning(f"Truncated log chunk from {len(log_chunk)} to {len(truncated)} chars")
        return truncated
    
    def format_log_chunk(
        self,
        logs: List[Dict[str, Any]],
        include_line_numbers: bool = True
    ) -> str:
        """
        Format log entries into a readable chunk for LLM.
        
        Args:
            logs: List of log entry dictionaries
            include_line_numbers: Whether to include line numbers
            
        Returns:
            Formatted log chunk string
        """
        lines = []
        
        for i, log in enumerate(logs, 1):
            if include_line_numbers:
                line_prefix = f"{i}. "
            else:
                line_prefix = ""
            
            # Format log entry
            log_parts = []
            for key, value in log.items():
                if value:
                    log_parts.append(f"{key}={value}")
            
            log_str = " | ".join(log_parts)
            lines.append(f"{line_prefix}{log_str}")
        
        return '\n'.join(lines)
    
    def get_available_modes(self) -> List[str]:
        """
        Get list of available prompt modes.
        
        Returns:
            List of mode names
        """
        modes = []
        for key in self.prompts.keys():
            if key.endswith('_mode'):
                mode_name = key.replace('_mode', '')
                modes.append(mode_name)
        
        return modes


class PromptValidator:
    """Validates prompt structure and content."""
    
    @staticmethod
    def validate_prompt_length(
        prompt: str,
        max_tokens: int = 4000,
        model_name: str = "llama3.2"
    ) -> tuple[bool, str]:
        """
        Validate prompt doesn't exceed model limits.
        
        Args:
            prompt: Prompt to validate
            max_tokens: Maximum allowed tokens
            model_name: Model name for context
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        estimated_tokens = len(prompt) // 4
        
        if estimated_tokens > max_tokens:
            return False, f"Prompt too long: {estimated_tokens} tokens (max {max_tokens})"
        
        return True, ""
    
    @staticmethod
    def validate_template_variables(
        template: str,
        variables: Dict[str, Any]
    ) -> tuple[bool, str]:
        """
        Validate that all template variables are provided.
        
        Args:
            template: Template string with {variables}
            variables: Dictionary of variable values
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        import re
        
        # Find all {variable} placeholders
        placeholders = re.findall(r'\{(\w+)\}', template)
        
        missing = [p for p in placeholders if p not in variables]
        
        if missing:
            return False, f"Missing template variables: {', '.join(missing)}"
        
        return True, ""

