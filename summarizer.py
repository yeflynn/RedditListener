"""
Gemini AI Summarization Module
Uses Google's Gemini API to summarize Reddit threads
"""
try:
    from google import genai
except ImportError:
    import google.generativeai as genai
import os
from typing import Optional

class ThreadSummarizer:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the summarizer with Gemini API
        
        Args:
            api_key: Gemini API key (if None, will try to get from environment)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            print("Warning: No Gemini API key provided. Summarization will not work.")
            self.model = None
        else:
            try:
                try:
                    # Try new API first
                    from google import genai as new_genai
                    client = new_genai.Client(api_key=self.api_key)
                    self.model = client.models.generate_content
                    self.use_new_api = True
                except:
                    # Fall back to old API
                    genai.configure(api_key=self.api_key)
                    self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    self.use_new_api = False
                print("Gemini AI initialized successfully")
            except Exception as e:
                print(f"Error initializing Gemini: {e}")
                self.model = None
    
    def summarize_thread(self, title: str, content: str) -> str:
        """
        Summarize a Reddit thread using Gemini AI
        
        Args:
            title: Thread title
            content: Thread content
            
        Returns:
            Summary text
        """
        if not self.model:
            return "Summarization unavailable - No API key configured"
        
        try:
            prompt = f"""Summarize the following Reddit thread in 2-3 concise sentences. 
Focus on the main issue, question, or story being discussed.

Title: {title}

Content: {content}

Provide a clear, objective summary:"""
            
            if hasattr(self, 'use_new_api') and self.use_new_api:
                response = self.model(model='gemini-2.0-flash-exp', contents=prompt)
                summary = response.text.strip()
            else:
                response = self.model.generate_content(prompt)
                summary = response.text.strip()
            
            return summary
            
        except Exception as e:
            print(f"Error generating summary: {e}")
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
