#!/usr/bin/env python3
import json
import os
import random
from datetime import datetime

# Create directory for formatted content
os.makedirs('formatted', exist_ok=True)

# Load the articles
with open('articles/latest_property_news.json', 'r') as f:
    articles = json.load(f)

# LinkedIn emojis and hashtags
linkedin_professional_phrases = [
    "Industry insights reveal that",
    "Market analysis shows",
    "Property professionals should note that",
    "Latest data indicates",
    "Emerging trends suggest",
    "Key developments in the sector include",
    "Property investors should be aware that",
    "Market intelligence suggests",
    "Industry experts highlight that",
    "New research demonstrates"
]

# Instagram emojis and hashtags
instagram_emojis = [
    "🏠", "🔑", "📈", "📉", "💰", "🏘️", "🏢", "🏡", "🔍", "📊",
    "💼", "🏆", "✅", "⭐", "📱", "🔐", "📝", "🔨", "🧰", "🌆"
]

instagram_hashtags = [
    "propertymarket", "realestate", "ukproperty", "propertyinvestment",
    "housingmarket", "propertynews", "landlords", "mortgages",
    "homebuyers", "propertytrends", "ukhousing", "rentalproperty",
    "propertydevelopment", "estateagent", "housingpolicy", "homeownership",
    "propertymanagement", "buytolet", "housingcrisis", "propertysales"
]

# Twitter emojis and hashtags
twitter_emojis = [
    "🏠", "🔑", "📈", "📉", "💰", "🏘️", "🏢", "🏡", "🔍", "📊"
]

twitter_hashtags = [
    "UKProperty", "RealEstate", "Housing", "PropertyNews", "PropTech",
    "Landlords", "Mortgages", "PropertyMarket", "HousingPolicy", "BuyToLet"
]

def create_linkedin_post(article):
    """Create a professional LinkedIn post"""
    intro_phrase = random.choice(linkedin_professional_phrases)
    
    # First paragraph - professional summary
    para1 = f"{intro_phrase} {article['title']}. {article['description'][:100]}..."
    
    # Second paragraph - call to action or insight
    source = article['source']
    date = article['date']
    para2 = f"This development from {source} on {date} highlights important shifts in the UK property landscape. Industry professionals should monitor these trends closely as they may impact investment strategies and market dynamics."
    
    return f"{para1}\n\n{para2}"

def create_instagram_post(article):
    """Create a casual, engaging Instagram post with emojis and hashtags"""
    # Select random emojis and hashtags
    emoji1, emoji2 = random.sample(instagram_emojis, 2)
    hashtag1, hashtag2 = random.sample(instagram_hashtags, 2)
    
    # Create engaging post with emojis
    title = article['title']
    description = article['description'][:100] + "..." if len(article['description']) > 100 else article['description']
    
    post = f"{emoji1} Hot off the press! {title} {emoji2}\n\n{description}\n\nWhat do you think about this? Let us know in the comments!\n\n#proptech #{hashtag1} #{hashtag2}"
    
    return post

def create_twitter_post(article):
    """Create a concise Twitter post under 280 characters with emoji and hashtag"""
    # Select random emoji and hashtag
    emoji = random.choice(twitter_emojis)
    hashtag = random.choice(twitter_hashtags)
    
    # Create concise post
    title = article['title']
    source = article['source']
    
    # Ensure the post is under 280 characters
    max_title_length = 200 - len(emoji) - len(hashtag) - len(source) - 15  # 15 for spacing and formatting
    if len(title) > max_title_length:
        title = title[:max_title_length-3] + "..."
    
    post = f"{emoji} {title} via {source} #{hashtag} #PropTech"
    
    # Ensure we're under 280 characters
    if len(post) > 280:
        post = post[:277] + "..."
    
    return post

def format_article_content(article):
    """Format an article for all three social media platforms"""
    linkedin = create_linkedin_post(article)
    instagram = create_instagram_post(article)
    twitter = create_twitter_post(article)
    
    formatted = f"Article: {article['title']}\nSource: {article['source']}\nDate: {article['date']}\nLink: {article['link']}\n\n"
    formatted += f"LinkedIn:\n{linkedin}\n\n"
    formatted += f"Instagram:\n{instagram}\n\n"
    formatted += f"Twitter:\n{twitter}\n\n"
    formatted += "-" * 80 + "\n\n"
    
    return formatted

# Process all articles and save formatted content
all_formatted_content = ""
for i, article in enumerate(articles[:10]):  # Process first 10 articles for demonstration
    print(f"Processing article {i+1}/{min(10, len(articles))}: {article['title']}")
    formatted = format_article_content(article)
    all_formatted_content += formatted
    
    # Save individual article formatting
    filename = f"formatted/article_{i+1:02d}_{article['date']}.txt"
    with open(filename, 'w') as f:
        f.write(formatted)

# Save all formatted content to a single file
today = datetime.now().strftime('%Y-%m-%d')
with open(f'formatted/all_articles_{today}.txt', 'w') as f:
    f.write(f"UK PROPERTY NEWS - SOCIAL MEDIA CONTENT - {today}\n\n")
    f.write(all_formatted_content)

print(f"Processed and saved formatted content for {min(10, len(articles))} articles")
