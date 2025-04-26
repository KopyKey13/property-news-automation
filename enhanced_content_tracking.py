#!/usr/bin/env python3
import os
import json
import hashlib
from datetime import datetime, timedelta
import re
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuration
HISTORY_FILE = 'articles/processed_articles_history.json'
PUBLISHED_POSTS_FILE = 'articles/published_posts_history.json'
MAX_HISTORY_DAYS = 30  # Keep track of articles for this many days
SIMILARITY_THRESHOLD = 0.8  # Threshold for content similarity (0.0 to 1.0)

def load_article_history():
    """Load history of processed articles."""
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No article history found or JSON file is invalid. Creating new history.")
        return {"processed_urls": [], "processed_dates": {}, "last_updated": datetime.now().isoformat()}

def load_published_posts_history():
    """Load history of posts that have been published to Google Sheets."""
    try:
        with open(PUBLISHED_POSTS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No published posts history found. Creating new history.")
        return {"published_posts": [], "last_updated": datetime.now().isoformat()}

def save_article_history(history):
    """Save history of processed articles."""
    # Ensure the articles directory exists
    os.makedirs('articles', exist_ok=True)
    
    # Update the last updated timestamp
    history["last_updated"] = datetime.now().isoformat()
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def save_published_posts_history(history):
    """Save history of published posts."""
    # Ensure the articles directory exists
    os.makedirs('articles', exist_ok=True)
    
    # Update the last updated timestamp
    history["last_updated"] = datetime.now().isoformat()
    
    with open(PUBLISHED_POSTS_FILE, 'w') as f:
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

def calculate_content_hash(content):
    """Calculate a hash of the content for similarity comparison."""
    # Normalize content: lowercase, remove extra spaces, etc.
    normalized_content = re.sub(r'\s+', ' ', content.lower()).strip()
    return hashlib.md5(normalized_content.encode('utf-8')).hexdigest()

def calculate_similarity(text1, text2):
    """Calculate similarity between two text strings."""
    # Convert to sets of words for simple similarity calculation
    words1 = set(re.findall(r'\b\w+\b', text1.lower()))
    words2 = set(re.findall(r'\b\w+\b', text2.lower()))
    
    # Calculate Jaccard similarity
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0

def is_post_similar_to_published(post_content, published_posts, threshold=SIMILARITY_THRESHOLD):
    """Check if a post is similar to any previously published post."""
    for published_post in published_posts:
        similarity = calculate_similarity(post_content, published_post)
        if similarity >= threshold:
            print(f"Found similar post with similarity {similarity:.2f} >= {threshold}")
            return True
    return False

def get_published_posts_from_sheet():
    """Get all posts that have been published to Google Sheets."""
    try:
        # Create credentials file from secret
        credentials_file = 'credentials.json'
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        
        if not sheet_id or not os.path.exists(credentials_file):
            print("Warning: Cannot access Google Sheet. Missing credentials or sheet ID.")
            return []
        
        # Load credentials from file
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        
        # Build the Sheets API service
        service = build('sheets', 'v4', credentials=credentials)
        
        # Get data from Google Sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='Sheet1'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print("No data found in Google Sheet.")
            return []
        
        # Find the content column
        headers = values[0]
        content_col = headers.index('Content') if 'Content' in headers else None
        
        if content_col is None:
            print("Warning: Content column not found in Google Sheet!")
            return []
        
        # Extract all content from the sheet
        published_contents = []
        for row in values[1:]:  # Skip header row
            if len(row) > content_col:
                published_contents.append(row[content_col])
        
        print(f"Found {len(published_contents)} published posts in Google Sheet.")
        return published_contents
    
    except Exception as e:
        print(f"Error accessing Google Sheet: {str(e)}")
        return []

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

def filter_new_posts(posts):
    """Filter out posts that are similar to previously published posts."""
    # Load published posts history
    published_history = load_published_posts_history()
    published_posts = published_history.get("published_posts", [])
    
    # Get posts from Google Sheet
    sheet_posts = get_published_posts_from_sheet()
    
    # Combine historical records with sheet data
    all_published_posts = published_posts + sheet_posts
    
    # Filter posts
    new_posts = []
    for post in posts:
        content = post.get("Content", "")
        
        # Skip posts without content
        if not content:
            continue
        
        # Check if this post is similar to any published post
        if not is_post_similar_to_published(content, all_published_posts):
            new_posts.append(post)
            
            # Track this post as published
            if content not in published_history["published_posts"]:
                published_history["published_posts"].append(content)
    
    # Save updated history
    save_published_posts_history(published_history)
    
    print(f"Filtered {len(posts)} posts to {len(new_posts)} new posts.")
    return new_posts

def filter_csv_file(csv_path):
    """Filter a CSV file to remove posts similar to previously published ones."""
    try:
        # Check if CSV file exists
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return
        
        # Read the CSV file
        df = pd.read_csv(csv_path)
        print(f"Read {len(df)} rows from CSV file.")
        
        # Convert DataFrame to list of dictionaries
        posts = df.to_dict('records')
        
        # Filter posts
        new_posts = filter_new_posts(posts)
        
        # Convert back to DataFrame
        new_df = pd.DataFrame(new_posts)
        
        # Save filtered CSV
        today = datetime.now().strftime('%Y-%m-%d')
        filtered_csv_path = f'exports/property_news_social_content_filtered_{today}.csv'
        new_df.to_csv(filtered_csv_path, index=False)
        
        # Also overwrite the original CSV to ensure only new content is used
        new_df.to_csv(csv_path, index=False)
        
        print(f"Saved {len(new_posts)} new posts to {filtered_csv_path} and {csv_path}")
        
    except Exception as e:
        print(f"Error filtering CSV file: {str(e)}")

def main():
    """Main function to track and filter articles and posts."""
    print("Starting enhanced content tracking system...")
    
    try:
        # First, filter articles
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
            print(f"Error filtering articles: {str(e)}")
        
        # Then, filter the CSV file with social media posts
        today = datetime.now().strftime('%Y-%m-%d')
        csv_path = f'exports/property_news_social_content_final_{today}.csv'
        filter_csv_file(csv_path)
        
    except Exception as e:
        print(f"Error in enhanced content tracking system: {str(e)}")

if __name__ == "__main__":
    main()
