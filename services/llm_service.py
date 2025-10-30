# -*- coding: utf-8 -*-
"""
LLM Service - Wrapper for Gemini text generation API
"""
from typing import Dict, Any, Optional
from services.gemini_client import GeminiClient, MissingAPIKey


def generate_text(system_prompt: str, user_prompt: str, temperature: float = 0.8, 
                 model: str = "gemini-2.5-flash", timeout: int = 180) -> str:
    """
    Generate text using Gemini API with specified temperature for creative output
    
    Args:
        system_prompt: System instruction for the LLM
        user_prompt: User prompt/query
        temperature: Controls randomness (0.0-1.0, higher = more creative)
        model: Gemini model to use
        timeout: Request timeout in seconds
        
    Returns:
        Generated text response
        
    Raises:
        MissingAPIKey: If no API key is configured
        Exception: For other API errors
    """
    client = GeminiClient(model=model)
    # Note: Current GeminiClient doesn't support temperature parameter
    # This is a placeholder for future enhancement
    return client.generate(system_prompt, user_prompt, timeout=timeout)


def generate_with_config(config: Dict[str, Any]) -> str:
    """
    Generate text using configuration dictionary
    
    Args:
        config: Dictionary with keys: system_prompt, user_prompt, temperature, model, timeout
        
    Returns:
        Generated text response
    """
    return generate_text(
        system_prompt=config.get("system_prompt", ""),
        user_prompt=config.get("user_prompt", ""),
        temperature=config.get("temperature", 0.8),
        model=config.get("model", "gemini-2.5-flash"),
        timeout=config.get("timeout", 180)
    )
