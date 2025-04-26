#!/usr/bin/env python3
import os
import json
import hashlib
from datetime import datetime, timedelta
import re

# Configuration
HISTORY_FILE = 'articles/processed_articles_history.json'
MAX_HISTORY_DAYS = 30  # Keep track of articles for this many days

def load_article_history():
    """Load history of processed articles."""
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No article history found or JSON file is invalid. Creating new history.")
        return {"processed_urls": [], "last_updated": datetime.now().isoformat()}

def save_article_history(history):
    """Save history of processed articles."""
    # Ensure the articles directory exists
    os.makedirs('articles', exist_ok=True)
    
    # Update the last updated timestamp
    history["last_updated"] = datetime.now().isoformat()
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def clean_old_history(history):
    """Remove entries older than MAX_HISTORY_DAYS."""
    if "processed_dates" not in history:
        history["processed_dates"] = {}
    
    cutoff_date = (datetime.now() - timedelta(days=MAX_HISTORY_DAYS)).isoformat()
    
    # Remove old dates
    history["processed_dates"] = {
        date: urls for date, urls in history["processed_dates"].items()
        if date >= cutoff_date
    }
    
    return history

def normalize_url(url):
    """Normalize URL to avoid duplicates with different query parameters."""
    # Remove query parameters and fragments
    url = re.sub(r'\?.*$', '', url)
    url = re.sub(r'#.*$', '', url)
    
    # Convert to lowercase
    url = url.lower()
    
    # Remove trailing slashes
    url = re.sub(r'/+$', '', url)
    
    return url

def is_article_processed(url, history):
    """Check if an article URL has been processed before."""
    normalized_url = normalize_url(url)
    
    # Check in all dates
    for date_urls in history.get("processed_dates", {}).values():
        if normalized_url in date_urls:
            return True
    
    return False

def track_processed_article(url, history, date=None):
    """Add an article URL to the processed history."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    normalized_url = normalize_url(url)
    
    if "processed_dates" not in history:
        history["processed_dates"] = {}
    
    if date not in history["processed_dates"]:
        history["processed_dates"][date] = []
    
    if normalized_url not in history["processed_dates"][date]:
        history["processed_dates"][date].append(normalized_url)
    
    return history

def filter_new_articles(articles):
    """Filter out articles that have been processed before."""
    # Load article history
    history = load_article_history()
    
    # Clean old history
    history = clean_old_history(history)
    
    # Filter articles
    new_articles = []
    for article in articles:
        url = article.get("link", "")
        
        # Skip articles without a URL
        if not url:
            continue
        
        # Check if this article has been processed before
        if not is_article_processed(url, history):
            new_articles.append(article)
            
            # Track this article as processed
            history = track_processed_article(url, history, article.get("date"))
    
    # Save updated history
    save_article_history(history)
    
    print(f"Filtered {len(articles)} articles to {len(new_articles)} new articles.")
    return new_articles

def main():
    """Main function to track and filter articles."""
    print("Starting content tracking system...")
    
    try:
        # Load existing articles
        with open('articles/latest_property_news.json', 'r') as f:
            articles = json.load(f)
        
        print(f"Loaded {len(articles)} articles.")
        
        # Filter to only new articles
        new_articles = filter_new_articles(articles)
        
        # Save filtered articles back to the file
        with open('articles/latest_property_news.json', 'w') as f:
            json.dump(new_articles, f, indent=2)
        
        print(f"Saved {len(new_articles)} new articles.")
        
    except Exception as e:
        print(f"Error in content tracking system: {str(e)}")

if __name__ == "__main__":
    main()
