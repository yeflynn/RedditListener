"""
Gemini AI Summarization Module
Uses Google's native Gemini SDK to summarize Reddit threads
"""
import google.generativeai as genai
import os
from typing import Optional
from logger_config import get_logger


class ThreadSummarizer:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the summarizer with Gemini API
        
        Args:
            api_key: Gemini API key (if None, will try to get from environment)
        """
        self.logger = get_logger('RedditListener')
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            self.logger.warning("No Gemini API key provided. Summarization will not work.")
            self.model = None
        else:
            try:
                # Configure the Gemini API
                genai.configure(api_key=self.api_key)
                
                # Get model name from environment or use default
                model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
                
                # Initialize the generative model
                self.model = genai.GenerativeModel(model_name)
                self.logger.info(f"Gemini AI initialized with native SDK using model: {model_name}")
                
            except Exception as e:
                self.logger.error(f"Error initializing Gemini: {e}", exc_info=True)
                self.model = None
    
    def summarize_thread(self, title: str, content: str, model: str = None) -> str:
        """
        Summarize a Reddit thread using Gemini AI
        
        Args:
            title: Thread title
            content: Thread content
            model: Gemini model to use (optional, overrides default)
            
        Returns:
            Summary text
        """
        if not self.model:
            self.logger.warning("Summarization attempted without API key")
            return "Summarization unavailable - No API key configured"
        
        try:
            self.logger.debug(f"Generating summary for thread: {title[:50]}...")
            
            # Use a different model if specified
            if model and model != os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'):
                current_model = genai.GenerativeModel(model)
                self.logger.debug(f"Using override model: {model}")
            else:
                current_model = self.model
                self.logger.debug(f"Using default model")
            
            prompt = f"""Summarize the following Reddit thread in 2-3 concise sentences. 
Focus on the main issue, question, or story being discussed.

Title: {title}

Content: {content}

Provide a clear, objective summary:"""
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=500,
                temperature=0.7,
            )
            
            # Generate the summary
            response = current_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract the text from response
            summary = response.text.strip()
            self.logger.info(f"Successfully generated summary ({len(summary)} chars) for: {title[:50]}...")
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating summary for '{title}': {e}", exc_info=True)
            return f"Error generating summary: {str(e)}"
    
    def batch_summarize(self, threads: list) -> dict:
        """
        Summarize multiple threads
        
        Args:
            threads: List of thread dictionaries with 'id', 'title', and 'content'
            
        Returns:
            Dictionary mapping thread IDs to summaries
        """
        summaries = {}
        
        for thread in threads:
            thread_id = thread.get('id')
            title = thread.get('title', '')
            content = thread.get('content', '')
            
            summary = self.summarize_thread(title, content)
            summaries[thread_id] = summary
            
        return summaries
    
    def list_available_models(self) -> list:
        """
        List all available Gemini models
        
        Returns:
            List of model names
        """
        try:
            models = []
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    models.append(model.name)
            return models
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            return []
