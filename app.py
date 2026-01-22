"""
RedditListener - Flask Web Application
Main application file
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Import our modules
from database import (
    init_database, insert_thread, get_all_threads, 
    get_thread_by_id, update_thread_summary, get_threads_without_summary
)
from reddit_scraper import RedditScraper
from summarizer import ThreadSummarizer

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize database on startup
init_database()

# Initialize scraper and summarizer
scraper = RedditScraper()
summarizer = ThreadSummarizer()

@app.route('/')
def index():
    """Home page with input form"""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_threads():
    """Handle thread download request"""
    try:
        # Get form data
        subreddit_url = request.form.get('subreddit_url', '').strip()
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        max_threads = int(request.form.get('max_threads', 10))
        
        if not subreddit_url:
            flash('Please provide a subreddit URL', 'error')
            return redirect(url_for('index'))
        
        if max_threads < 1 or max_threads > 100:
            flash('Max threads must be between 1 and 100', 'error')
            return redirect(url_for('index'))
        
        # Scrape threads
        flash(f'Downloading threads from {subreddit_url}...', 'info')
        threads = scraper.scrape_subreddit(subreddit_url, max_threads)
        
        if not threads:
            flash('No threads found or error occurred during scraping', 'error')
            return redirect(url_for('index'))
        
        # Filter by date range if provided
        if start_date and end_date:
            threads = scraper.filter_by_date_range(threads, start_date, end_date)
            flash(f'Filtered to {len(threads)} threads within date range', 'info')
        
        # Save to database
        saved_count = 0
        for thread in threads:
            if insert_thread(thread):
                saved_count += 1
        
        flash(f'Successfully downloaded and saved {saved_count} threads!', 'success')
        return redirect(url_for('view_threads'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/threads')
def view_threads():
    """Display all downloaded threads"""
    threads = get_all_threads()
    return render_template('threads.html', threads=threads)

@app.route('/thread/<int:thread_id>')
def view_thread(thread_id):
    """Display a single thread with its summary"""
    thread = get_thread_by_id(thread_id)
    
    if not thread:
        flash('Thread not found', 'error')
        return redirect(url_for('view_threads'))
    
    return render_template('thread_detail.html', thread=thread)

@app.route('/summarize/<int:thread_id>', methods=['POST'])
def summarize_thread(thread_id):
    """Generate summary for a specific thread"""
    thread = get_thread_by_id(thread_id)
    
    if not thread:
        return jsonify({'error': 'Thread not found'}), 404
    
    try:
        # Generate summary
        summary = summarizer.summarize_thread(
            thread['title'], 
            thread['content']
        )
        
        # Update database
        update_thread_summary(thread_id, summary)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/summarize_all', methods=['POST'])
def summarize_all_threads():
    """Generate summaries for all threads without summaries"""
    try:
        threads = get_threads_without_summary()
        
        if not threads:
            flash('All threads already have summaries!', 'info')
            return redirect(url_for('view_threads'))
        
        summarized_count = 0
        for thread in threads:
            try:
                summary = summarizer.summarize_thread(
                    thread['title'],
                    thread['content']
                )
                update_thread_summary(thread['id'], summary)
                summarized_count += 1
            except Exception as e:
                print(f"Error summarizing thread {thread['id']}: {e}")
                continue
        
        flash(f'Successfully summarized {summarized_count} threads!', 'success')
        return redirect(url_for('view_threads'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('view_threads'))

@app.route('/api/threads')
def api_threads():
    """API endpoint to get all threads as JSON"""
    threads = get_all_threads()
    return jsonify(threads)

@app.route('/api/thread/<int:thread_id>')
def api_thread(thread_id):
    """API endpoint to get a specific thread as JSON"""
    thread = get_thread_by_id(thread_id)
    if thread:
        return jsonify(thread)
    return jsonify({'error': 'Thread not found'}), 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
