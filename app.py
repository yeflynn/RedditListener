"""
RedditListener - Flask Web Application
Main application file
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from datetime import datetime, timedelta
import os
import json
import time
import uuid
from dotenv import load_dotenv

# Import our modules
from database import (
    init_database, insert_thread, get_all_threads, 
    get_thread_by_id, update_thread_summary, get_threads_without_summary,
    clear_all_threads, get_threads_by_tag, get_all_unique_tags
)
from reddit_scraper import RedditScraper
from summarizer import ThreadSummarizer
from logger_config import setup_logger, get_logger

# Load environment variables
load_dotenv()

# Initialize logger
logger = setup_logger('RedditListener')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize database on startup
logger.info('Initializing database...')
init_database()
logger.info('Database initialized successfully')

# Initialize scraper and summarizer
logger.info('Initializing Reddit scraper and AI summarizer...')
scraper = RedditScraper()
summarizer = ThreadSummarizer()
logger.info('Scraper and summarizer initialized successfully')

# Store progress data in memory
progress_data = {}

@app.route('/')
def index():
    """Home page with input form"""
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_threads():
    """Redirect to progress-enabled download"""
    return download_with_progress()

@app.route('/download_with_progress', methods=['POST'])
def download_with_progress():
    """Handle thread download request"""
    try:
        # Get form data
        subreddit_url = request.form.get('subreddit_url', '').strip()
        skip_date_filter = request.form.get('skip_date_filter') == 'on'
        start_date = request.form.get('start_date', '') if not skip_date_filter else ''
        end_date = request.form.get('end_date', '') if not skip_date_filter else ''
        max_threads = int(request.form.get('max_threads', 10))
        gemini_model = request.form.get('gemini_model', 'gemini-2.5-flash')
        
        logger.info(f'Download request received: subreddit={subreddit_url}, max_threads={max_threads}, skip_date_filter={skip_date_filter}, date_range={start_date} to {end_date}, gemini_model={gemini_model}')
        
        if not subreddit_url:
            logger.warning('Download request rejected: No subreddit URL provided')
            flash('Please provide a subreddit URL', 'error')
            return redirect(url_for('index'))
        
        if max_threads < 1 or max_threads > 100:
            logger.warning(f'Download request rejected: Invalid max_threads={max_threads}')
            flash('Max threads must be between 1 and 100', 'error')
            return redirect(url_for('index'))
        
        # Generate unique progress ID
        progress_id = str(uuid.uuid4())
        logger.info(f'Generated progress ID: {progress_id}')
        
        # Store parameters for the download process
        progress_data[progress_id] = {
            'status': 'starting',
            'subreddit_url': subreddit_url,
            'start_date': start_date,
            'end_date': end_date,
            'max_threads': max_threads,
            'gemini_model': gemini_model,
            'saved_count': 0,
            'completed': False
        }
        
        # Render progress page
        return render_template('download_progress.html', 
                             progress_id=progress_id,
                             subreddit_url=subreddit_url,
                             max_threads=max_threads)
        
    except Exception as e:
        logger.error(f'Error in download_with_progress: {str(e)}', exc_info=True)
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/threads')
def view_threads():
    """Display all downloaded threads with optional tag filtering"""
    # Get filter tag from query parameter
    filter_tag = request.args.get('tag', '')
    
    if filter_tag:
        threads = get_threads_by_tag(filter_tag)
    else:
        threads = get_all_threads()
    
    # Get all unique tags for the filter dropdown
    all_tags = get_all_unique_tags()
    
    return render_template('threads.html', threads=threads, all_tags=all_tags, current_tag=filter_tag)

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
    """Generate summary and tags for a specific thread"""
    thread = get_thread_by_id(thread_id)
    
    if not thread:
        return jsonify({'error': 'Thread not found'}), 404
    
    try:
        # Get model from request or use default
        # Use force=True to parse JSON even if Content-Type is not set correctly
        data = request.get_json(force=True, silent=True) or {}
        model = data.get('model', os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'))
        
        # Generate summary and tags
        result = summarizer.summarize_and_tag_thread(
            thread['title'], 
            thread['content'],
            model=model
        )
        
        summary = result['summary']
        tags = result['tags']
        tags_str = ','.join(tags) if tags else ''
        
        # Update database with summary and tags
        update_thread_summary(thread_id, summary, tags_str)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'tags': tags
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/summarize_all', methods=['POST'])
def summarize_all_threads():
    """Generate summaries and tags for all threads without summaries"""
    try:
        threads = get_threads_without_summary()
        
        if not threads:
            flash('All threads already have summaries!', 'info')
            return redirect(url_for('view_threads'))
        
        summarized_count = 0
        for thread in threads:
            try:
                result = summarizer.summarize_and_tag_thread(
                    thread['title'],
                    thread['content']
                )
                summary = result['summary']
                tags = result['tags']
                tags_str = ','.join(tags) if tags else ''
                update_thread_summary(thread['id'], summary, tags_str)
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

@app.route('/clear_all', methods=['POST'])
def clear_all():
    """Clear all threads from the database"""
    try:
        if clear_all_threads():
            logger.info('All threads cleared from database')
            flash('All threads have been cleared from the database!', 'success')
        else:
            logger.error('Failed to clear threads from database')
            flash('Error clearing threads', 'error')
    except Exception as e:
        logger.error(f'Error in clear_all route: {str(e)}', exc_info=True)
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('view_threads'))


@app.route('/progress_stream/<progress_id>')
def progress_stream(progress_id):
    """Server-Sent Events stream for real-time progress"""
    logger.info(f'Progress stream started for ID: {progress_id}')
    
    def generate():
        if progress_id not in progress_data:
            logger.warning(f'Invalid progress ID requested: {progress_id}')
            yield f"data: {json.dumps({'error': 'Invalid progress ID'})}\n\n"
            return
        
        # Start the download process
        try:
            data = progress_data[progress_id]
            subreddit_url = data['subreddit_url']
            start_date = data['start_date']
            end_date = data['end_date']
            max_threads = data['max_threads']
            
            # Send initial message
            yield f"data: {json.dumps({'message': f'🚀 Starting download from {subreddit_url}...', 'type': 'info'})}\n\n"
            time.sleep(0.5)
            
            # Scrape threads with progress updates
            logger.info(f'Starting scrape: {subreddit_url}, max_threads={max_threads}')
            yield f"data: {json.dumps({'message': f'📡 Fetching threads (max: {max_threads})...', 'type': 'info'})}\n\n"
            threads = scraper.scrape_subreddit(subreddit_url, max_threads)
            logger.info(f'Scrape completed: Found {len(threads) if threads else 0} threads')
            
            if not threads:
                logger.warning(f'No threads found for {subreddit_url}')
                yield f"data: {json.dumps({'message': '❌ No threads found or error occurred', 'type': 'error'})}\n\n"
                yield f"data: {json.dumps({'completed': True, 'saved_count': 0})}\n\n"
                return
            
            yield f"data: {json.dumps({'message': f'✅ Found {len(threads)} threads', 'type': 'success'})}\n\n"
            time.sleep(0.3)
            
            # Filter by date range if provided
            if start_date and end_date:
                yield f"data: {json.dumps({'message': f'📅 Filtering by date range...', 'type': 'info'})}\n\n"
                original_count = len(threads)
                threads = scraper.filter_by_date_range(threads, start_date, end_date)
                logger.info(f'Date filtering: {len(threads)}/{original_count} threads match range {start_date} to {end_date}')
                yield f"data: {json.dumps({'message': f'📊 Filtered: {len(threads)}/{original_count} threads match date range', 'type': 'info'})}\n\n"
                time.sleep(0.3)
            
            # Save to database with progress
            yield f"data: {json.dumps({'message': f'💾 Saving threads to database...', 'type': 'info'})}\n\n"
            saved_count = 0
            
            for i, thread in enumerate(threads, 1):
                if insert_thread(thread):
                    saved_count += 1
                    title_preview = thread['title'][:50] + '...' if len(thread['title']) > 50 else thread['title']
                    logger.debug(f'Saved thread {i}/{len(threads)}: {thread["title"]}')
                    yield f"data: {json.dumps({'message': f'✓ Saved ({i}/{len(threads)}): {title_preview}', 'type': 'progress'})}\n\n"
                    time.sleep(0.2)  # Small delay for visibility
                else:
                    logger.debug(f'Skipped duplicate thread {i}/{len(threads)}: {thread["title"]}')
                    yield f"data: {json.dumps({'message': f'⊘ Skipped ({i}/{len(threads)}): Duplicate thread', 'type': 'warning'})}\n\n"
            
            # Final summary
            logger.info(f'Download completed: Saved {saved_count} threads from {subreddit_url}')
            yield f"data: {json.dumps({'message': f'🎉 Successfully saved {saved_count} threads!', 'type': 'success'})}\n\n"
            time.sleep(0.5)
            
            # Send completion signal
            yield f"data: {json.dumps({'completed': True, 'saved_count': saved_count})}\n\n"
            
            # Update progress data
            data['completed'] = True
            data['saved_count'] = saved_count
            
        except Exception as e:
            logger.error(f'Error in progress_stream: {str(e)}', exc_info=True)
            yield f"data: {json.dumps({'message': f'❌ Error: {str(e)}', 'type': 'error'})}\n\n"
            yield f"data: {json.dumps({'completed': True, 'saved_count': 0})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
