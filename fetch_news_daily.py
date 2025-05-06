#!/usr/bin/env python3
import os
import feedparser
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import time
from dateutil import parser as date_parser

# List of RSS feeds to fetch
RSS_FEEDS = [
    "https://www.progressiveproperty.co.uk/blog",
    "https://www.propertyhub.net/feed/",
    "https://www.property118.com/feed/",
    "https://www.propertyinvestortoday.co.uk/rss",
    "http://www.rightmove.co.uk/news/feed",
    "https://energysavingtrust.org.uk/feed/",
    "https://www.nationwidehousepriceindex.co.uk/feed/rss",
    "https://www.homesandproperty.co.uk/rss",
    "https://hmlandregistry.blog.gov.uk/feed/",
    "https://www.zoopla.co.uk/discover/property-news/"
]

# Create directories if they don't exist
os.makedirs('articles', exist_ok=True)
os.makedirs('exports', exist_ok=True)

def clean_html(html_content):
    """Remove HTML tags and clean up the content."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_recent_article(pub_date):
    """Check if the article is from 2024 or 2025."""
    if not pub_date:
        return False
    
    try:
        date_obj = date_parser.parse(pub_date)
        year = date_obj.year
        return year >= 2024
    except:
        return False

def fetch_articles():
    """Fetch articles from RSS feeds and return a list of recent articles."""
    all_articles = []
    
    for feed_url in RSS_FEEDS:
        try:
            print(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                # Extract article information
                title = entry.get('title', '')
                link = entry.get('link', '')
                pub_date = entry.get('published', '')
                
                # Try alternative date fields if 'published' is not available
                if not pub_date and 'pubDate' in entry:
                    pub_date = entry.pubDate
                if not pub_date and 'updated' in entry:
                    pub_date = entry.updated
                
                # Skip articles that are not from 2024 or 2025
                if not is_recent_article(pub_date):
                    continue
                
                # Extract description/content
                description = ""
                if 'description' in entry:
                    description = clean_html(entry.description)
                elif 'summary' in entry:
                    description = clean_html(entry.summary)
                elif 'content' in entry:
                    for content in entry.content:
                        description += clean_html(content.value) + " "
                
                # Create article object
                article = {
                    'title': title,
                    'link': link,
                    'pub_date': pub_date,
                    'description': description,
                    'source': feed.feed.get('title', feed_url)
                }
                
                all_articles.append(article)
            
            print(f"Fetched {len(feed.entries)} articles from {feed_url}")
            
        except Exception as e:
            print(f"Error fetching feed {feed_url}: {str(e)}")
    
    # Sort articles by publication date (newest first)
    all_articles.sort(key=lambda x: date_parser.parse(x['pub_date']) if x['pub_date'] else datetime.min, reverse=True)
    
    # Limit to the most recent articles (enough to create 2 posts per platform per day)
    # We need 6 articles (2 each for LinkedIn, Twitter, Instagram)
    recent_articles = all_articles[:10]  # Get a few extra in case some are filtered out later
    
    return recent_articles

def save_articles(articles):
    """Save articles to a JSON file."""
    today = datetime.now().strftime('%Y-%m-%d')
    output_file = f'articles/latest_property_news.json'
    
    with open(output_file, 'w') as f:
        json.dump(articles, f, indent=2)
    
    print(f"Saved {len(articles)} articles to {output_file}")
    return output_file

if __name__ == "__main__":
    articles = fetch_articles()
    save_articles(articles)
    print(f"Fetched and saved {len(articles)} recent property news articles.")
