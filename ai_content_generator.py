#!/usr/bin/env python3
import os
import json
import random
import requests
from datetime import datetime, timedelta
import uuid
import time

# Configuration
MIN_ARTICLES_NEEDED = 6  # 2 posts per platform (LinkedIn, Instagram, Twitter)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PROPERTY_TOPICS = [
    "HMO investment strategies in the UK",
    "Rent-to-Rent (R2R) opportunities in today's market",
    "UK property investment trends",
    "Serviced Accommodation market analysis",
    "Buy, Refurbish, Refinance, Rent (BRRR) strategy tips",
    "Legal changes affecting UK landlords",
    "UK property market forecast",
    "Tax implications for property investors",
    "Property technology innovations",
    "Energy efficiency regulations for UK properties",
    "First-time buyer market trends",
    "Commercial to residential conversions",
    "Rental yield optimization strategies",
    "Property management best practices",
    "UK mortgage market updates"
]

def load_existing_articles():
    """Load existing articles from the JSON file."""
    try:
        with open('articles/latest_property_news.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No existing articles found or JSON file is invalid. Creating new file.")
        return []

def save_articles(articles):
    """Save articles to the JSON file."""
    # Ensure the articles directory exists
    os.makedirs('articles', exist_ok=True)
    
    with open('articles/latest_property_news.json', 'w') as f:
        json.dump(articles, f, indent=2)

def get_article_urls(articles):
    """Extract URLs from existing articles to avoid duplicates."""
    return [article.get('link', '') for article in articles]

def generate_ai_content(topic):
    """Generate property news content using OpenAI API."""
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set.")
        return None
    
    current_year = datetime.now().year
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        prompt = f"""Write a factual, informative UK property news article about {topic}. 
        The article should:
        - Be based on current trends and facts (no older than 2-3 years)
        - Focus specifically on the UK property market
        - Include relevant statistics or expert opinions
        - Be approximately 300-400 words
        - Have a clear headline/title
        - Be written in a professional journalistic style
        - Include a brief summary at the end
        
        The article should be current as of {current_year} and contain only factual information.
        """
        
        data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 800
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            
            # Extract title from the content (assuming it's the first line)
            lines = content.strip().split('\n')
            title = lines[0].replace('#', '').strip()
            if title.startswith('"') and title.endswith('"'):
                title = title[1:-1].strip()
            
            # Remove the title from the content
            article_content = '\n'.join(lines[1:]).strip()
            
            return {
                "title": title,
                "content": article_content
            }
        else:
            print(f"Error from OpenAI API: {response.status_code}")
            print(response.text)
            return None
    
    except Exception as e:
        print(f"Error generating content: {str(e)}")
        return None

def create_article_object(content_data, topic):
    """Create a standardized article object from AI-generated content."""
    now = datetime.now()
    article_id = str(uuid.uuid4())
    
    return {
        "title": content_data["title"],
        "link": f"https://propertymarketanalysis.uk/article/{article_id}",
        "pub_date": now.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        "date": now.strftime("%Y-%m-%d"),
        "source": "Property Market Analysis",
        "content": content_data["content"],
        "summary": content_data["content"][:150] + "...",
        "topic": topic,
        "ai_generated": True
    }

def generate_needed_articles(existing_articles):
    """Generate additional articles if needed."""
    # Count how many articles we already have
    article_count = len(existing_articles)
    
    # Calculate how many more we need
    articles_needed = max(0, MIN_ARTICLES_NEEDED - article_count)
    
    if articles_needed <= 0:
        print(f"Found {article_count} articles, which is sufficient (minimum needed: {MIN_ARTICLES_NEEDED}).")
        return existing_articles
    
    print(f"Found only {article_count} articles. Generating {articles_needed} more with AI.")
    
    # Get existing URLs to avoid duplicates
    existing_urls = get_article_urls(existing_articles)
    
    # Generate new articles
    new_articles = []
    topics_to_use = random.sample(PROPERTY_TOPICS, min(articles_needed, len(PROPERTY_TOPICS)))
    
    for i, topic in enumerate(topics_to_use):
        print(f"Generating article {i+1}/{articles_needed} on topic: {topic}")
        
        # Add some delay to avoid rate limits
        if i > 0:
            time.sleep(2)
        
        content_data = generate_ai_content(topic)
        if content_data:
            article = create_article_object(content_data, topic)
            
            # Ensure we don't have duplicate URLs (extremely unlikely with UUID)
            if article["link"] not in existing_urls:
                new_articles.append(article)
                print(f"Successfully generated article: {article['title']}")
            else:
                print(f"Skipping duplicate article with URL: {article['link']}")
    
    # Combine existing and new articles, sort by publication date (newest first)
    all_articles = existing_articles + new_articles
    all_articles.sort(key=lambda x: datetime.strptime(x.get("pub_date", ""), "%a, %d %b %Y %H:%M:%S +0000"), reverse=True)
    
    return all_articles

def main():
    """Main function to check for articles and generate more if needed."""
    print("Starting AI content generator...")
    
    # Ensure we have the OpenAI API key
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY environment variable not set.")
        print("Please set this environment variable with your OpenAI API key.")
        return
    
    # Load existing articles
    existing_articles = load_existing_articles()
    print(f"Loaded {len(existing_articles)} existing articles.")
    
    # Generate additional articles if needed
    updated_articles = generate_needed_articles(existing_articles)
    
    # Save all articles back to the JSON file
    save_articles(updated_articles)
    print(f"Saved {len(updated_articles)} articles to JSON file.")
    
    # Count AI-generated articles
    ai_generated_count = sum(1 for article in updated_articles if article.get("ai_generated", False))
    print(f"Total articles: {len(updated_articles)} ({ai_generated_count} AI-generated)")

if __name__ == "__main__":
    main()
