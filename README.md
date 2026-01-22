# 🎧 RedditListener

A web application to download, store, and analyze Reddit threads with AI-powered summaries using Google's Gemini AI.

## Features

- **📥 Thread Download**: Scrape threads from any subreddit
- **📅 Date Range Filtering**: Filter threads by date range
- **🗄️ Local Storage**: Store threads in SQLite database
- **📊 Thread Display**: View all downloaded threads in a clean interface
- **✨ AI Summarization**: Generate summaries using Gemini AI
- **🔍 Thread Details**: View individual threads with full content and summaries

## Screenshots

### Home Page
Input form to download threads from subreddits with date range and max threads options.

### Threads List
View all downloaded threads with options to generate AI summaries.

### Thread Detail
View full thread content with AI-generated summary.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Gemini API key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/RedditListener.git
   cd RedditListener
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Gemini API key:
   ```
   GEMINI_API_KEY=your-api-key-here
   SECRET_KEY=your-secret-key-here
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Open in browser**
   Navigate to `http://localhost:5000`

## Usage

### Download Threads

1. Go to the home page
2. Enter a subreddit URL or name (e.g., `r/FacebookMarketplace` or `https://www.reddit.com/r/FacebookMarketplace/`)
3. Optionally set a date range
4. Set the maximum number of threads to download (1-100)
5. Click "Download Threads"

### View Threads

- Navigate to the "View Threads" page to see all downloaded threads
- Click on any thread title to view full details
- Use the "Generate Summary" button to create AI summaries for individual threads
- Use "Summarize All" to generate summaries for all threads at once

### Thread Details

- View full thread content
- See AI-generated summary
- Link to original Reddit post

## Project Structure

```
RedditListener/
├── app.py                  # Main Flask application
├── database.py             # Database operations
├── reddit_scraper.py       # Reddit web scraping
├── summarizer.py           # Gemini AI integration
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── templates/             # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── threads.html
│   └── thread_detail.html
└── static/                # Static files
    └── css/
        └── style.css
```

## Technologies Used

- **Backend**: Flask (Python web framework)
- **Database**: SQLite
- **Web Scraping**: BeautifulSoup4, Requests
- **AI**: Google Gemini AI
- **Frontend**: HTML, CSS, JavaScript

## API Endpoints

- `GET /` - Home page
- `POST /download` - Download threads
- `GET /threads` - View all threads
- `GET /thread/<id>` - View specific thread
- `POST /summarize/<id>` - Generate summary for thread
- `POST /summarize_all` - Generate summaries for all threads
- `GET /api/threads` - Get all threads as JSON
- `GET /api/thread/<id>` - Get specific thread as JSON

## Limitations

- Web scraping may be affected by Reddit's page structure changes
- Reddit API rate limits may apply
- Gemini API has usage quotas
- Date filtering is approximate based on relative time strings

## Future Enhancements

- [ ] Reddit API integration (PRAW)
- [ ] Export threads to CSV/JSON
- [ ] Search and filter functionality
- [ ] User authentication
- [ ] Scheduled scraping
- [ ] More AI analysis options

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Disclaimer

This tool is for educational purposes. Please respect Reddit's Terms of Service and robots.txt when scraping data.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

Built with ❤️ using Flask and Gemini AI
