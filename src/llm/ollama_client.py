"""Ollama API client for LLM integration."""

import json
import requests
from typing import Dict, Any, Optional, List
from ..utils.logger import setup_logger
from ..utils.exceptions import LLMError

logger = setup_logger()


class OllamaClient:
    """
    Client for interacting with Ollama API.
    
    Supports text generation with JSON formatting and model health checks.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama API base URL
            model: Default model name (auto-detects if None)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Auto-detect model if not specified
        if model is None:
            available_models = self.list_models()
            if available_models:
                # Prefer llama models
                for preferred in ["llama3.2", "llama3.1", "llama3", "llama2"]:
                    matching = [m for m in available_models if preferred in m.lower()]
                    if matching:
                        model = matching[0]
                        logger.info(f"Auto-detected model: {model}")
                        break
                
                if model is None:
                    model = available_models[0]
                    logger.info(f"Using first available model: {model}")
            else:
                model = "llama3.2"  # Fallback default
                logger.warning(f"No models detected, using default: {model}")
        
        self.model = model
        
        logger.info(f"Initialized OllamaClient (base_url={base_url}, model={model})")
    
    def health_check(self) -> bool:
        """
        Check if Ollama server is running and accessible.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                logger.info(f"Ollama health check passed. Available models: {len(models)}")
                return True
            else:
                logger.warning(f"Ollama health check failed with status {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    def list_models(self) -> List[str]:
        """
        List available models on Ollama server.
        
        Returns:
            List of model names
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            logger.info(f"Found {len(model_names)} available models")
            return model_names
            
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        format_json: bool = False,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: Input prompt for the model
            model: Model name (uses default if None)
            format_json: If True, force JSON output format
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text or JSON string
            
        Raises:
            LLMError: If generation fails
        """
        model = model or self.model
        
        logger.debug(f"Generating with model={model}, format_json={format_json}")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
        
        # Request JSON format
        if format_json:
            payload["format"] = "json"
        
        # Add max tokens if specified
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        # Attempt generation with retries
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries}")
                
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
                generated_text = result.get('response', '')
                
                logger.info(
                    f"Generation successful: {len(generated_text)} chars, "
                    f"took {result.get('total_duration', 0) / 1e9:.2f}s"
                )
                
                return generated_text
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise LLMError(f"Generation timed out after {self.max_retries} attempts")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed on attempt {attempt + 1}: {e}")
                if attempt == self.max_retries - 1:
                    raise LLMError(f"Generation failed: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise LLMError(f"Unexpected error during generation: {e}")
        
        raise LLMError("Generation failed after all retry attempts")
    
    def generate_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate JSON-formatted response.
        
        Args:
            prompt: Input prompt
            model: Model name
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            LLMError: If generation or JSON parsing fails
        """
        response_text = self.generate(
            prompt=prompt,
            model=model,
            format_json=True,
            system_prompt=system_prompt,
            temperature=temperature
        )
        
        try:
            parsed_json = json.loads(response_text)
            logger.debug(f"Successfully parsed JSON response with {len(parsed_json)} keys")
            return parsed_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")
            raise LLMError(f"Invalid JSON response from model: {e}")
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        format_json: bool = False
    ) -> str:
        """
        Chat-style generation with message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            format_json: If True, force JSON output
            
        Returns:
            Generated response text
        """
        model = model or self.model
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        if format_json:
            payload["format"] = "json"
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            return result.get('message', {}).get('content', '')
            
        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            raise LLMError(f"Chat failed: {e}")
    
    def get_model_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a specific model.
        
        Args:
            model: Model name (uses default if None)
            
        Returns:
            Model information dictionary
        """
        model = model or self.model
        
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": model},
                timeout=5
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return {}

