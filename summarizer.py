"""
Gemini AI Summarization Module
Uses Google's native Gemini SDK to summarize Reddit threads
"""
import google.generativeai as genai
import os
from typing import Optional, Dict, List, Tuple
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
    
    # Available tags for classification
    AVAILABLE_TAGS = ['Scam', 'Product Quality', 'User Experience']
    
    def summarize_thread(self, title: str, content: str, model: str = None) -> str:
        """
        Summarize a Reddit thread using Gemini AI (legacy method for backward compatibility)
        
        Args:
            title: Thread title
            content: Thread content
            model: Gemini model to use (optional, overrides default)
            
        Returns:
            Summary text
        """
        result = self.summarize_and_tag_thread(title, content, model)
        return result['summary']
    
    def summarize_and_tag_thread(self, title: str, content: str, model: str = None) -> Dict:
        """
        Summarize a Reddit thread and classify it with relevant tags using Gemini AI
        
        Args:
            title: Thread title
            content: Thread content
            model: Gemini model to use (optional, overrides default)
            
        Returns:
            Dictionary with 'summary' and 'tags' keys
        """
        if not self.model:
            self.logger.warning("Summarization attempted without API key")
            return {
                'summary': "Summarization unavailable - No API key configured",
                'tags': []
            }
        
        try:
            self.logger.debug(f"Generating summary and tags for thread: {title[:50]}...")
            
            # Use a different model if specified
            if model and model != os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'):
                current_model = genai.GenerativeModel(model)
                self.logger.debug(f"Using override model: {model}")
            else:
                current_model = self.model
                self.logger.debug(f"Using default model")
            
            prompt = f"""Analyze the following Reddit thread and provide:
1. A summary in 2-3 concise sentences focusing on the main issue, question, or story.
2. Classification tags from this list: Scam, Product Quality, User Experience
   - "Scam" if the post reports or discusses scams, fraud, or deceptive practices
   - "Product Quality" if the post discusses product defects, quality issues, or reliability problems
   - "User Experience" if the post discusses customer service, buying/selling experience, or platform usability
   - A post can have multiple tags or no tags if none apply

Title: {title}

Content: {content}

Respond in this exact format:
SUMMARY: [Your 2-3 sentence summary here]
TAGS: [Comma-separated tags, or "None" if no tags apply]"""
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=1000,
                temperature=0.7,
            )
            
            # Generate the response
            response = current_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Parse the response
            response_text = response.text.strip()
            summary, tags = self._parse_summary_and_tags(response_text)
            
            self.logger.info(f"Successfully generated summary ({len(summary)} chars) and tags ({tags}) for: {title[:50]}...")
            
            return {
                'summary': summary,
                'tags': tags
            }
            
        except Exception as e:
            self.logger.error(f"Error generating summary for '{title}': {e}", exc_info=True)
            return {
                'summary': f"Error generating summary: {str(e)}",
                'tags': []
            }
    
    def _parse_summary_and_tags(self, response_text: str) -> Tuple[str, List[str]]:
        """
        Parse the AI response to extract summary and tags
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Tuple of (summary, list of tags)
        """
        summary = ""
        tags = []
        
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.upper().startswith('SUMMARY:'):
                summary = line[8:].strip()
            elif line.upper().startswith('TAGS:'):
                tags_str = line[5:].strip()
                if tags_str.lower() != 'none' and tags_str:
                    # Parse comma-separated tags and validate against allowed tags
                    raw_tags = [t.strip() for t in tags_str.split(',')]
                    for tag in raw_tags:
                        # Match against available tags (case-insensitive)
                        for valid_tag in self.AVAILABLE_TAGS:
                            if tag.lower() == valid_tag.lower():
                                tags.append(valid_tag)
                                break
        
        # If parsing failed, use the whole response as summary
        if not summary:
            summary = response_text
        
        return summary, tags
    
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
