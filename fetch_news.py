#!/usr/bin/env python3
import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from dateutil import parser
import time
import os

# Create directories for storing data
os.makedirs('articles', exist_ok=True)
os.makedirs('formatted', exist_ok=True)

# List of RSS feed URLs
rss_feeds = [
    "https://propertyindustryeye.com/feed/",
    "https://www.estateagenttoday.co.uk/rss",
    "https://www.propertyreporter.co.uk/rss/news",
    "https://www.landlordtoday.co.uk/rss",
    "https://www.property118.com/feed/",
    "https://rss.app/feeds/_GpyXXg4aOeD2FglM.xml",
    "https://www.insidehousing.co.uk/rss"
]

# Function to parse date from various formats
def parse_date(date_str):
    try:
        return parser.parse(date_str)
    except:
        return None

# Function to fetch and parse RSS feeds
def fetch_rss_feeds():
    all_articles = []
    
    for feed_url in rss_feeds:
        try:
            print(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                # Extract article data
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                # Handle different date formats
                published_date = None
                if 'published' in entry:
                    published_date = parse_date(entry.published)
                elif 'pubDate' in entry:
                    published_date = parse_date(entry.pubDate)
                elif 'updated' in entry:
                    published_date = parse_date(entry.updated)
                
                # Skip if no date found
                if not published_date:
                    continue
                
                # Format date for consistency
                date_str = published_date.strftime('%Y-%m-%d')
                
                # Extract description/summary
                description = ''
                if 'description' in entry:
                    description = entry.description
                elif 'summary' in entry:
                    description = entry.summary
                
                # Clean HTML from description
                soup = BeautifulSoup(description, 'html.parser')
                clean_description = soup.get_text().strip()
                
                # Create article object
                article = {
                    'title': title,
                    'link': link,
                    'date': date_str,
                    'date_obj': published_date,
                    'description': clean_description,
                    'source': feed.feed.get('title', feed_url)
                }
                
                all_articles.append(article)
                
        except Exception as e:
            print(f"Error fetching feed {feed_url}: {str(e)}")
    
    return all_articles

# Function to filter articles by date
def filter_articles_by_date(articles, start_year=2024):
    filtered_articles = []
    current_year = datetime.now().year
    
    for article in articles:
        try:
            article_year = article['date_obj'].year
            if start_year <= article_year <= current_year:
                filtered_articles.append(article)
        except:
            # Skip articles with invalid dates
            continue
    
    return filtered_articles

# Function to save articles to file
def save_articles(articles, filename='articles.json'):
    # Sort articles by date (newest first)
    sorted_articles = sorted(articles, key=lambda x: x['date_obj'], reverse=True)
    
    # Remove date_obj for JSON serialization
    for article in sorted_articles:
        if 'date_obj' in article:
            del article['date_obj']
    
    with open(filename, 'w') as f:
        json.dump(sorted_articles, f, indent=2)
    
    return sorted_articles

# Main execution
if __name__ == "__main__":
    print("Fetching property news articles...")
    all_articles = fetch_rss_feeds()
    print(f"Found {len(all_articles)} articles in total")
    
    filtered_articles = filter_articles_by_date(all_articles)
    print(f"Filtered to {len(filtered_articles)} articles from 2024-2025")
    
    saved_articles = save_articles(filtered_articles, 'articles/latest_property_news.json')
    print(f"Saved {len(saved_articles)} articles to articles/latest_property_news.json")
