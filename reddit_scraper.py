"""
Reddit Scraper Module
Scrapes threads from Reddit subreddits using web scraping
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional
import time

class RedditScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def extract_subreddit_name(self, url: str) -> Optional[str]:
        """Extract subreddit name from URL"""
        # Match patterns like /r/subreddit or reddit.com/r/subreddit or just r/subreddit
        match = re.search(r'/?r/([^/]+)', url)
        if match:
            return match.group(1)
        return None
    
    def parse_relative_time(self, time_str: str) -> str:
        """Convert relative time (e.g., '2 hr. ago') to approximate date"""
        try:
            now = datetime.now()
            time_str = time_str.lower().strip()
            
            if 'just now' in time_str or 'now' in time_str:
                return now.isoformat()
            
            # Extract number and unit
            match = re.search(r'(\d+)\s*(min|hr|hour|day|week|month|year)', time_str)
            if not match:
                return now.isoformat()
            
            value = int(match.group(1))
            unit = match.group(2)
            
            if 'min' in unit:
                delta = timedelta(minutes=value)
            elif 'hr' in unit or 'hour' in unit:
                delta = timedelta(hours=value)
            elif 'day' in unit:
                delta = timedelta(days=value)
            elif 'week' in unit:
                delta = timedelta(weeks=value)
            elif 'month' in unit:
                delta = timedelta(days=value * 30)
            elif 'year' in unit:
                delta = timedelta(days=value * 365)
            else:
                delta = timedelta(0)
            
            return (now - delta).isoformat()
        except:
            return datetime.now().isoformat()
    
    def scrape_subreddit(self, subreddit_url: str, max_threads: int = 10) -> List[Dict]:
        """
        Scrape threads from a subreddit
        
        Args:
            subreddit_url: URL of the subreddit
            max_threads: Maximum number of threads to scrape
            
        Returns:
            List of thread dictionaries
        """
        threads = []
        subreddit_name = self.extract_subreddit_name(subreddit_url)
        
        if not subreddit_name:
            print(f"Could not extract subreddit name from URL: {subreddit_url}")
            return threads
        
        # Normalize URL
        if not subreddit_url.startswith('http'):
            subreddit_url = f'https://www.reddit.com/r/{subreddit_name}/'
        
        try:
            print(f"Fetching threads from {subreddit_url}...")
            response = requests.get(subreddit_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all post elements (shreddit-post tags)
            posts = soup.find_all('shreddit-post', limit=max_threads * 2)  # Get more to filter
            
            print(f"Found {len(posts)} post elements")
            
            for post in posts:
                if len(threads) >= max_threads:
                    break
                
                try:
                    # Extract post ID
                    post_id = post.get('id', '').replace('t3_', '')
                    if not post_id:
                        continue
                    
                    # Extract text content from the post
                    post_text = post.get_text(separator=' ', strip=True)
                    
                    # Parse the text to extract components
                    lines = [line.strip() for line in post_text.split('\n') if line.strip()]
                    
                    # Try to find title, author, and time
                    title = None
                    author = None
                    posted_time = None
                    flair = None
                    content = ""
                    
                    # Look for patterns in the text
                    for i, line in enumerate(lines):
                        # Author pattern (u/username)
                        if line.startswith('u/') and not author:
                            author = line
                            # Check if next line is time
                            if i + 1 < len(lines) and ('ago' in lines[i + 1] or 'hr' in lines[i + 1]):
                                posted_time = lines[i + 1]
                        
                        # Time pattern
                        elif 'ago' in line or ('hr' in line and '.' in line):
                            if not posted_time:
                                posted_time = line
                        
                        # Flair patterns
                        elif line in ['Discussion', 'Scam', 'Support', 'Question', 'Meta']:
                            flair = line
                        
                        # Title is usually one of the longer lines before content
                        elif len(line) > 20 and not title and 'ago' not in line:
                            title = line
                    
                    # If we couldn't parse well, try alternative method
                    if not title:
                        # Get all text and take first substantial line
                        for line in lines:
                            if len(line) > 15 and 'u/' not in line and 'ago' not in line:
                                title = line
                                break
                    
                    # Content is usually after the metadata
                    content_start = False
                    content_parts = []
                    for line in lines:
                        if content_start and line not in [title, author, posted_time, flair]:
                            content_parts.append(line)
                        elif line == flair or (posted_time and line == posted_time):
                            content_start = True
                    
                    content = ' '.join(content_parts[:3]) if content_parts else post_text[:200]
                    
                    if title:
                        thread_data = {
                            'thread_id': post_id,
                            'subreddit': subreddit_name,
                            'title': title,
                            'author': author or 'Unknown',
                            'posted_time': posted_time or 'Unknown',
                            'created_date': self.parse_relative_time(posted_time) if posted_time else datetime.now().isoformat(),
                            'flair': flair or 'General',
                            'content': content,
                            'url': f'https://www.reddit.com/r/{subreddit_name}/comments/{post_id}/'
                        }
                        
                        threads.append(thread_data)
                        print(f"Scraped: {title[:50]}...")
                
                except Exception as e:
                    print(f"Error parsing post: {e}")
                    continue
            
            print(f"Successfully scraped {len(threads)} threads")
            
        except requests.RequestException as e:
            print(f"Error fetching subreddit: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        return threads
    
    def filter_by_date_range(self, threads: List[Dict], start_date: str, end_date: str) -> List[Dict]:
        """
        Filter threads by date range
        
        Args:
            threads: List of thread dictionaries
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Filtered list of threads
        """
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            
            filtered = []
            for thread in threads:
                try:
                    thread_date = datetime.fromisoformat(thread['created_date'])
                    if start <= thread_date <= end:
                        filtered.append(thread)
                except:
                    # If date parsing fails, include the thread
                    filtered.append(thread)
            
            return filtered
        except:
            # If date range parsing fails, return all threads
            return threads
