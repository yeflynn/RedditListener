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
import random
from logger_config import get_logger

class RedditScraper:
    def __init__(self):
        self.logger = get_logger('RedditListener')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        self.last_request_time = 0
        self.min_request_interval = 5  # Minimum 5 seconds between requests
        self.max_request_interval = 8  # Maximum 8 seconds (adds randomness)
    
    def extract_subreddit_name(self, url: str) -> Optional[str]:
        """Extract subreddit name from URL"""
        # Clean up the URL first
        url = url.strip()
        
        # Match patterns like /r/subreddit or reddit.com/r/subreddit or just r/subreddit
        match = re.search(r'/?r/([^/\s?&#]+)', url, re.IGNORECASE)
        if match:
            subreddit = match.group(1).strip()
            self.logger.info(f"Extracted subreddit name: '{subreddit}' from URL: '{url}'")
            return subreddit
        
        self.logger.error(f"Could not extract subreddit name from: '{url}'")
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
    
    def scrape_subreddit(self, subreddit_url: str, max_threads: int = 10, fetch_full_content: bool = True) -> List[Dict]:
        """
        Scrape threads from a subreddit
        
        Args:
            subreddit_url: URL of the subreddit
            max_threads: Maximum number of threads to scrape
            fetch_full_content: Whether to fetch full content from each thread page (slower but more complete)
            
        Returns:
            List of thread dictionaries
        """
        threads = []
        subreddit_name = self.extract_subreddit_name(subreddit_url)
        
        if not subreddit_name:
            self.logger.error(f"Could not extract subreddit name from URL: {subreddit_url}")
            return threads
        
        # Normalize URL - use old.reddit.com for better scraping (shows 25 posts per page)
        # Always sort by 'new' to get the latest posts
        if not subreddit_url.startswith('http'):
            subreddit_url = f'https://old.reddit.com/r/{subreddit_name}/new/'
        else:
            # Convert to old.reddit.com (avoid double 'old' prefix)
            if 'old.reddit.com' not in subreddit_url:
                # Replace www.reddit.com first, then plain reddit.com (but not if already replaced)
                if 'www.reddit.com' in subreddit_url:
                    subreddit_url = subreddit_url.replace('www.reddit.com', 'old.reddit.com')
                elif 'reddit.com' in subreddit_url:
                    subreddit_url = subreddit_url.replace('reddit.com', 'old.reddit.com')
            # Ensure trailing slash
            if not subreddit_url.endswith('/'):
                subreddit_url += '/'
            # Add /new/ to sort by newest if not already specified
            if '/new' not in subreddit_url and '/hot' not in subreddit_url and '/top' not in subreddit_url and '/rising' not in subreddit_url:
                subreddit_url = subreddit_url.rstrip('/') + '/new/'
        
        try:
            # Rate limiting to avoid blocks with random delay
            if self.last_request_time > 0:  # Skip delay on first request
                random_delay = random.uniform(self.min_request_interval, self.max_request_interval)
                current_time = time.time()
                time_since_last_request = current_time - self.last_request_time
                
                if time_since_last_request < random_delay:
                    sleep_time = random_delay - time_since_last_request
                    self.logger.info(f"Rate limiting: sleeping for {sleep_time:.1f} seconds (random delay)")
                    time.sleep(sleep_time)
            
            self.logger.info(f"Fetching threads from {subreddit_url}...")
            response = requests.get(subreddit_url, headers=self.headers, timeout=10)
            self.last_request_time = time.time()
            response.raise_for_status()
            self.logger.debug(f"HTTP response status: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try both old Reddit and new Reddit post structures
            # Old Reddit uses <div class="thing" data-type="link">
            # New Reddit uses <shreddit-post>
            posts = soup.find_all('shreddit-post', limit=max_threads * 5)
            
            if len(posts) < max_threads:
                # Try old Reddit structure
                self.logger.info(f"Found {len(posts)} new Reddit posts, trying old Reddit structure...")
                old_posts = soup.find_all('div', {'class': 'thing', 'data-type': 'link'}, limit=max_threads * 2)
                if old_posts:
                    posts = old_posts
                    self.logger.info(f"Using old Reddit structure, found {len(posts)} posts")
            
            self.logger.info(f"Found {len(posts)} post elements on page")
            
            for post in posts:
                if len(threads) >= max_threads:
                    break
                
                try:
                    # Detect if this is old Reddit or new Reddit structure
                    is_old_reddit = post.name == 'div' and 'thing' in post.get('class', [])
                    
                    if is_old_reddit:
                        # Old Reddit parsing
                        post_id = post.get('data-fullname', '').replace('t3_', '')
                        if not post_id:
                            post_id = post.get('id', '').replace('thing_t3_', '')
                        
                        # Extract title
                        title_elem = post.find('a', {'class': 'title'})
                        title = title_elem.get_text(strip=True) if title_elem else None
                        
                        # Extract author
                        author_elem = post.find('a', {'class': 'author'})
                        author = f"u/{author_elem.get_text(strip=True)}" if author_elem else 'Unknown'
                        
                        # Extract time
                        time_elem = post.find('time')
                        posted_time = time_elem.get('title', 'Unknown') if time_elem else 'Unknown'
                        
                        # Extract flair
                        flair_elem = post.find('span', {'class': 'linkflairlabel'})
                        flair = flair_elem.get_text(strip=True) if flair_elem else 'General'
                        
                        # Extract URL
                        url_elem = post.find('a', {'class': 'title'})
                        url = f"https://old.reddit.com{url_elem.get('href', '')}" if url_elem else f'https://old.reddit.com/r/{subreddit_name}/comments/{post_id}/'
                        
                        # Extract content (try multiple sources)
                        content = ''
                        
                        # Try 1: Self-text for text posts
                        expando_elem = post.find('div', {'class': 'expando'})
                        if expando_elem:
                            usertext = expando_elem.find('div', {'class': 'usertext-body'})
                            if usertext:
                                content = usertext.get_text(separator=' ', strip=True)[:1000]
                        
                        # Try 2: Get post metadata/description
                        if not content:
                            entry = post.find('div', {'class': 'entry'})
                            if entry:
                                # Get all text from entry except buttons/links
                                content = entry.get_text(separator=' ', strip=True)[:500]
                        
                        # Try 3: Just use title as content if nothing else
                        if not content or len(content) < 20:
                            content = f"Link post: {title}" if title else "No content available"
                        
                        self.logger.debug(f"Processing old Reddit post {len(threads)+1}/{max_threads}, post_id: {post_id}")
                        
                    else:
                        # New Reddit parsing (existing logic)
                        post_id = post.get('id', '').replace('t3_', '')
                        self.logger.debug(f"Processing new Reddit post {len(threads)+1}/{max_threads}, post_id: {post_id}")
                        if not post_id:
                            self.logger.debug("Skipping post: No post_id found")
                            continue
                        
                        # Extract text content from the post
                        post_text = post.get_text(separator=' ', strip=True)
                        self.logger.debug(f"Raw post text length: {len(post_text)} chars")
                        
                        # Log entire raw thread text for debugging
                        self.logger.debug(f"Raw thread text for post {post_id}:")
                        self.logger.debug(f"{'='*80}")
                        self.logger.debug(post_text)
                        self.logger.debug(f"{'='*80}")
                        
                        # Parse the text to extract components
                        lines = [line.strip() for line in post_text.split('\n') if line.strip()]
                        
                        # Try to find title, author, and time
                        title = None
                        author = None
                        posted_time = None
                        flair = None
                        content = ""
                    
                    # Only do complex parsing for new Reddit
                    if not is_old_reddit:
                        # Known flair patterns
                        known_flairs = ['Discussion', 'Scam', 'Support', 'Question', 'Meta', 'General', 'Rumor', 'News']
                        
                        # Look for patterns in the text
                        for i, line in enumerate(lines):
                            # Extract title from line (may contain u/username)
                            if len(line) > 20 and not title and 'ago' not in line:
                                # Check if line contains u/username pattern
                                if 'u/' in line:
                                    # Extract text before u/username as title
                                    match = re.match(r'^(.+?)\s+u/[\w-]+', line)
                                    if match:
                                        title = match.group(1).strip()
                                        # Also extract author if present
                                        author_match = re.search(r'u/([\w-]+)', line)
                                        if author_match and not author:
                                            author = 'u/' + author_match.group(1)
                                else:
                                    title = line
                            
                            # Author pattern (u/username) on separate line
                            if line.startswith('u/') and not author:
                                author = line
                                # Check if next line is time
                                if i + 1 < len(lines) and ('ago' in lines[i + 1] or 'hr' in lines[i + 1]):
                                    posted_time = lines[i + 1]
                            
                            # Time pattern
                            if 'ago' in line or ('hr' in line and '.' in line):
                                if not posted_time:
                                    posted_time = line
                            
                            # Flair patterns
                            if line in known_flairs:
                                flair = line
                    
                        # Clean up title - remove metadata patterns (only for new Reddit)
                        if title:
                            # Remove author mentions (u/username)
                            title = re.sub(r'\s*u/[\w-]+\s*', ' ', title)
                            # Remove bullet points and separators
                            title = re.sub(r'\s*[•·]\s*', ' ', title)
                            # Remove known flairs
                            for flair_text in known_flairs:
                                title = title.replace(flair_text, '')
                            # Remove extra whitespace
                            title = ' '.join(title.split())
                            # If title appears twice (common pattern), take first occurrence
                            words = title.split()
                            if len(words) > 10:
                                # Check if first half repeats
                                half = len(words) // 2
                                first_half = ' '.join(words[:half])
                                if first_half in title[len(first_half):]:
                                    title = first_half
                            title = title.strip()
                        
                        # If we couldn't parse well, try alternative method
                        if not title or len(title) < 3:
                            # Get all text and take first substantial line (lowered threshold)
                            for line in lines:
                                if len(line) > 10 and 'u/' not in line and 'ago' not in line:
                                    # Clean this title too
                                    title = re.sub(r'\s*u/[\w-]+\s*', ' ', line)
                                    title = re.sub(r'\s*[•·]\s*', ' ', title)
                                    title = ' '.join(title.split()).strip()
                                    if len(title) >= 3:
                                        break
                        
                        # Ultimate fallback: use first non-empty line or post_id
                        if not title or len(title) < 3:
                            if lines:
                                title = lines[0][:100]  # Take first line, max 100 chars
                            else:
                                title = f"Post {post_id}"  # Last resort: use post ID
                        
                        # Content is usually after the metadata
                        content_start = False
                        content_parts = []
                        for line in lines:
                            if content_start and line not in [title, author, posted_time, flair]:
                                content_parts.append(line)
                            elif line == flair or (posted_time and line == posted_time):
                                content_start = True
                        
                        content = ' '.join(content_parts[:3]) if content_parts else post_text[:200]
                    
                    # Always save the thread (never skip)
                    created_date = self.parse_relative_time(posted_time) if posted_time else datetime.now().isoformat()
                    thread_data = {
                        'thread_id': post_id,
                        'subreddit': subreddit_name,
                        'title': title,
                        'author': author or 'Unknown',
                        'posted_time': posted_time or 'Unknown',
                        'created_date': created_date,
                        'flair': flair or 'General',
                        'content': content,
                        'url': f'https://www.reddit.com/r/{subreddit_name}/comments/{post_id}/'
                    }
                    
                    self.logger.debug(f"Parsed thread: title='{title[:60]}...', author={author}, posted_time={posted_time}, created_date={created_date}")
                    
                    # Fetch full content from thread page if enabled
                    if fetch_full_content:
                        self.logger.info(f"Fetching full content for thread {len(threads)+1}/{max_threads}...")
                        full_content = self.fetch_thread_content(thread_data['url'])
                        if full_content:
                            thread_data['content'] = full_content
                            self.logger.debug(f"Updated content with {len(full_content)} chars")
                    
                    threads.append(thread_data)
                    self.logger.info(f"Successfully scraped thread {len(threads)}/{max_threads}: {title[:60]}...")
                
                except Exception as e:
                    self.logger.error(f"Error parsing post {post_id if 'post_id' in locals() else 'unknown'}: {e}", exc_info=True)
                    continue
            
            self.logger.info(f"Successfully scraped {len(threads)} threads from {subreddit_name}")
            
        except requests.HTTPError as e:
            if e.response.status_code == 403:
                self.logger.error(f"Access blocked by Reddit (403 Forbidden). Reddit may be rate-limiting or blocking automated requests.")
                self.logger.error(f"Try again in a few minutes, or consider using Reddit's official API.")
            else:
                self.logger.error(f"HTTP error fetching threads: {e}")
            return []
        except requests.RequestException as e:
            self.logger.error(f"Error fetching threads: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error scraping {subreddit_url}: {e}", exc_info=True)
            return []
        
        return threads
    
    def fetch_thread_content(self, thread_url: str) -> str:
        """
        Fetch post content by visiting the individual thread page
        
        Args:
            thread_url: URL of the thread to fetch
            
        Returns:
            Post body content (self-text only, no comments)
        """
        try:
            # Convert to old.reddit.com for better scraping
            if 'old.reddit.com' not in thread_url:
                if 'www.reddit.com' in thread_url:
                    thread_url = thread_url.replace('www.reddit.com', 'old.reddit.com')
                elif 'reddit.com' in thread_url:
                    thread_url = thread_url.replace('reddit.com', 'old.reddit.com')
            
            # Rate limiting
            if self.last_request_time > 0:
                random_delay = random.uniform(self.min_request_interval, self.max_request_interval)
                current_time = time.time()
                time_since_last_request = current_time - self.last_request_time
                
                if time_since_last_request < random_delay:
                    sleep_time = random_delay - time_since_last_request
                    self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.1f}s")
                    time.sleep(sleep_time)
            
            self.logger.debug(f"Fetching post content from: {thread_url}")
            response = requests.get(thread_url, headers=self.headers, timeout=15)
            self.last_request_time = time.time()
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the main post area (not comments)
            # Old Reddit: the first usertext-body inside the main post, not in comments
            post_area = soup.find('div', {'class': 'expando'})
            if post_area:
                usertext = post_area.find('div', {'class': 'usertext-body'})
                if usertext:
                    # Get the markdown div for cleaner text
                    md_div = usertext.find('div', {'class': 'md'})
                    if md_div:
                        post_body = md_div.get_text(separator='\n', strip=True)
                    else:
                        post_body = usertext.get_text(separator='\n', strip=True)
                    
                    if post_body and len(post_body) > 10:
                        self.logger.debug(f"Fetched {len(post_body)} chars of post content")
                        return post_body[:3000]  # Limit to 3000 chars
            
            # Fallback: try to find any self-text in the top-level post
            # Look for the sitetable thing with the post
            thing = soup.find('div', {'class': 'thing', 'data-type': 'link'})
            if thing:
                expando = thing.find('div', {'class': 'expando'})
                if expando:
                    usertext = expando.find('div', {'class': 'usertext-body'})
                    if usertext:
                        post_body = usertext.get_text(separator='\n', strip=True)
                        if post_body and len(post_body) > 10:
                            self.logger.debug(f"Fetched {len(post_body)} chars of post content (fallback)")
                            return post_body[:3000]
            
            self.logger.debug("No post content found (may be a link post)")
            return ""
                
        except Exception as e:
            self.logger.error(f"Error fetching thread content from {thread_url}: {e}")
            return ""
    
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
            # Set end date to end of day (23:59:59) to include the entire end date
            end = datetime.fromisoformat(end_date + 'T23:59:59')
            self.logger.info(f"Filtering threads by date range: {start_date} to {end_date}")
            self.logger.debug(f"Start datetime: {start}, End datetime: {end}")
            
            filtered = []
            for i, thread in enumerate(threads, 1):
                try:
                    thread_date = datetime.fromisoformat(thread['created_date'])
                    in_range = start <= thread_date <= end
                    
                    self.logger.debug(f"Thread {i}/{len(threads)}: '{thread['title'][:40]}...'")
                    self.logger.debug(f"  - Posted time: {thread.get('posted_time', 'Unknown')}")
                    self.logger.debug(f"  - Created date: {thread['created_date']}")
                    self.logger.debug(f"  - Parsed datetime: {thread_date}")
                    self.logger.debug(f"  - In range ({start_date} to {end_date}): {in_range}")
                    
                    if in_range:
                        filtered.append(thread)
                        self.logger.info(f"✓ Thread {i} INCLUDED: {thread['title'][:50]}...")
                    else:
                        self.logger.info(f"✗ Thread {i} EXCLUDED: {thread['title'][:50]}... (date: {thread_date.date()})")
                        
                except Exception as e:
                    # If date parsing fails, include the thread
                    self.logger.warning(f"Thread {i} date parsing failed ({e}), including by default: {thread['title'][:50]}...")
                    filtered.append(thread)
            
            self.logger.info(f"Date filtering complete: {len(filtered)}/{len(threads)} threads match range")
            return filtered
        except Exception as e:
            # If date range parsing fails, return all threads
            self.logger.error(f"Date range parsing failed: {e}, returning all threads", exc_info=True)
            return threads
