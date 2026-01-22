"""
Gemini AI Summarization Module
Uses Google's Gemini API to summarize Reddit threads
Supports both OpenAI-compatible endpoint and native Google API
"""
from openai import OpenAI
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
        # Try OPENAI_API_KEY first (for Manus sandbox), then GEMINI_API_KEY
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            self.logger.warning("No Gemini API key provided. Summarization will not work.")
            self.client = None
            self.api_type = None
        else:
            try:
                # Detect API type based on key format
                if self.api_key.startswith('AIzaSy'):
                    # Native Google Gemini API key
                    self.api_type = 'google'
                    # Use OpenAI client with Google's endpoint
                    self.client = OpenAI(
                        api_key=self.api_key,
                        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
                    )
                    self.logger.info("Gemini AI initialized with Google endpoint")
                else:
                    # OpenAI-compatible API key (Manus sandbox)
                    self.api_type = 'openai'
                    self.client = OpenAI(api_key=self.api_key)
                    self.logger.info("Gemini AI initialized with OpenAI-compatible endpoint")
            except Exception as e:
                self.logger.error(f"Error initializing Gemini: {e}", exc_info=True)
                self.client = None
                self.api_type = None
    
    def summarize_thread(self, title: str, content: str, model: str = None) -> str:
        """
        Summarize a Reddit thread using Gemini AI
        
        Args:
            title: Thread title
            content: Thread content
            model: Gemini model to use (default: gemini-2.0-flash-exp)
            
        Returns:
            Summary text
        """
        if not self.client:
            self.logger.warning("Summarization attempted without API key")
            return "Summarization unavailable - No API key configured"
        
        try:
            self.logger.debug(f"Generating summary for thread: {title[:50]}...")
            prompt = f"""Summarize the following Reddit thread in 2-3 concise sentences. 
Focus on the main issue, question, or story being discussed.

Title: {title}

Content: {content}

Provide a clear, objective summary:"""
            
            # Use provided model or default
            if not model:
                model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
            
            self.logger.debug(f"Using model: {model}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=200
            )
            summary = response.choices[0].message.content.strip()
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
