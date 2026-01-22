"""
Gemini AI Summarization Module
Uses Google's Gemini API via OpenAI-compatible interface to summarize Reddit threads
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
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            self.logger.warning("No Gemini API key provided. Summarization will not work.")
            self.client = None
        else:
            try:
                # Use OpenAI-compatible API
                self.client = OpenAI(api_key=self.api_key)
                self.logger.info("Gemini AI initialized successfully")
            except Exception as e:
                self.logger.error(f"Error initializing Gemini: {e}", exc_info=True)
                self.client = None
    
    def summarize_thread(self, title: str, content: str) -> str:
        """
        Summarize a Reddit thread using Gemini AI
        
        Args:
            title: Thread title
            content: Thread content
            
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
            
            response = self.client.chat.completions.create(
                model='gemini-2.5-flash',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=200
            )
            summary = response.choices[0].message.content.strip()
            self.logger.info(f"Successfully generated summary for: {title[:50]}...")
            
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
