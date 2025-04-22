#!/usr/bin/env python3
import os
import json
import random
from datetime import datetime
import re

# Create directories if they don't exist
os.makedirs('formatted', exist_ok=True)

# Load articles from JSON file
def load_articles():
    """Load articles from the JSON file."""
    input_file = 'articles/latest_property_news.json'
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return []
    
    with open(input_file, 'r') as f:
        articles = json.load(f)
    
    print(f"Loaded {len(articles)} articles from {input_file}")
    return articles

# LinkedIn post creation
def create_linkedin_post(article):
    """Create a LinkedIn post for the given article."""
    title = article['title']
    link = article['link']
    description = article['description']
    
    # Professional introductions for LinkedIn
    intros = [
        "Industry experts highlight that",
        "Latest data indicates",
        "Market intelligence suggests",
        "Property professionals should note that",
        "New developments in the sector reveal",
        "Industry insights reveal that",
        "Market analysis shows",
        "Property market update:"
    ]
    
    # Create the post
    intro = random.choice(intros)
    
    # First paragraph: Introduction and key point
    if len(description) > 150:
        first_para = f"{intro} {title}. {description[:150]}..."
    else:
        first_para = f"{intro} {title}. {description}"
    
    # Second paragraph: Call to action
    second_para = f"Read the full article to learn more about the implications for property investors and industry professionals: {link}"
    
    # Combine paragraphs
    post = f"{first_para}\n\n{second_para}"
    
    return post

# Instagram post creation
def create_instagram_post(article):
    """Create an Instagram post for the given article."""
    title = article['title']
    
    # Casual introductions for Instagram
    intros = [
        "🏠 Hot off the press!",
        "🔑 Property alert!",
        "🏘️ Trending in real estate:",
        "🏢 Breaking property news:",
        "📊 Market update:",
        "🏡 Property insight:",
        "💼 Real estate buzz:"
    ]
    
    # Emojis for Instagram
    emojis = ["🏠", "🔑", "🏘️", "🏢", "📊", "🏡", "💼", "🌆", "📈", "📉", "💰", "🔍", "📱"]
    
    # Hashtags for Instagram
    hashtags = ["#propertymarket", "#realestate", "#propertyinvestment", "#ukproperty", 
                "#propertyinvestor", "#propertydevelopment", "#housingmarket", "#property", 
                "#investment", "#realestateinvesting", "#propertymanagement", "#landlord"]
    
    # Create the post
    intro = random.choice(intros)
    emoji1 = random.choice(emojis)
    emoji2 = random.choice([e for e in emojis if e != emoji1])
    
    # Select 2 random hashtags plus #proptech
    selected_hashtags = random.sample(hashtags, 2)
    selected_hashtags.append("#proptech")
    
    # Create a casual, engaging post
    post = f"{intro} {title} {emoji1}\n\n"
    post += f"Stay updated with the latest trends in the UK property market! {emoji2}\n\n"
    post += " ".join(selected_hashtags)
    
    return post

# Twitter post creation
def create_twitter_post(article):
    """Create a Twitter post for the given article."""
    title = article['title']
    link = article['link']
    
    # Emojis for Twitter
    emojis = ["🏠", "🔑", "🏘️", "🏢", "📊", "🏡", "💼", "🌆", "📈", "📉", "💰", "🔍", "📱"]
    
    # Hashtags for Twitter
    hashtags = ["#PropertyMarket", "#RealEstate", "#UKProperty", "#Housing", "#PropTech", 
                "#Investment", "#Property", "#Landlord", "#HousingMarket"]
    
    # Create the post
    emoji = random.choice(emojis)
    hashtag = random.choice(hashtags)
    
    # Ensure the post is under 280 characters
    max_title_length = 200 - len(link) - len(hashtag) - len(emoji) - 5  # 5 for spaces and punctuation
    
    if len(title) > max_title_length:
        title = title[:max_title_length] + "..."
    
    post = f"{emoji} {title} {link} {hashtag}"
    
    return post

def create_social_content():
    """Create social media content for each article."""
    articles = load_articles()
    
    if not articles:
        print("No articles to process.")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    output_file = f'formatted/all_articles_{today}.txt'
    
    # Create content for each platform (2 posts per platform)
    platforms = ['LinkedIn', 'Instagram', 'Twitter']
    posts_per_platform = 2
    
    # Dictionary to store posts by platform
    platform_posts = {platform: [] for platform in platforms}
    
    # Create posts for each article
    for i, article in enumerate(articles):
        if i >= posts_per_platform * len(platforms):
            break  # We have enough posts
            
        # Determine which platform to create content for
        platform_index = i % len(platforms)
        platform = platforms[platform_index]
        
        # Skip if we already have enough posts for this platform
        if len(platform_posts[platform]) >= posts_per_platform:
            continue
            
        # Create content based on platform
        if platform == 'LinkedIn':
            post = create_linkedin_post(article)
        elif platform == 'Instagram':
            post = create_instagram_post(article)
        elif platform == 'Twitter':
            post = create_twitter_post(article)
        
        # Add to platform posts
        platform_posts[platform].append({
            'date': today,
            'platform': platform,
            'content': post,
            'article_title': article['title'],
            'article_link': article['link']
        })
    
    # Write all content to a single file
    with open(output_file, 'w') as f:
        for platform in platforms:
            for post in platform_posts[platform]:
                f.write(f"Date: {post['date']}\n")
                f.write(f"Platform: {platform}\n")
                f.write(f"Article: {post['article_title']}\n")
                f.write(f"Link: {post['article_link']}\n")
                f.write(f"Content:\n{post['content']}\n\n")
                f.write("-" * 80 + "\n\n")
    
    print(f"Created social media content for {sum(len(posts) for posts in platform_posts.values())} posts.")
    
    # Save as JSON for further processing
    json_output = f'formatted/social_content_{today}.json'
    all_posts = []
    for platform, posts in platform_posts.items():
        all_posts.extend(posts)
    
    with open(json_output, 'w') as f:
        json.dump(all_posts, f, indent=2)
    
    print(f"Saved social media content to {json_output}")
    return json_output

if __name__ == "__main__":
    create_social_content()
