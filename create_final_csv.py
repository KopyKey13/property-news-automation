#!/usr/bin/env python3
import json
import csv
import os
from datetime import datetime
from collections import defaultdict

# Create directory for exports
os.makedirs('exports', exist_ok=True)

# Load the articles
with open('articles/latest_property_news.json', 'r') as f:
    articles = json.load(f)

# Create CSV file for Google Sheets with updated format
today = datetime.now().strftime('%Y-%m-%d')
csv_filename = f'exports/property_news_social_content_final_{today}.csv'

# Group articles by date
articles_by_date = defaultdict(list)
for article in articles:
    date = article['date']
    articles_by_date[date].append(article)

# Dictionary to store content by date and platform
content_by_date_platform = defaultdict(list)

# Process articles
for i, article in enumerate(articles):
    try:
        # Generate content for each platform
        from create_social_content import create_linkedin_post, create_instagram_post, create_twitter_post
        
        # Generate content for each platform
        linkedin_content = create_linkedin_post(article)
        instagram_content = create_instagram_post(article)
        twitter_content = create_twitter_post(article)
        
        # Store content by date and platform
        date = article['date']
        content_by_date_platform[(date, 'LinkedIn')].append(linkedin_content)
        content_by_date_platform[(date, 'Instagram')].append(instagram_content)
        content_by_date_platform[(date, 'Twitter')].append(twitter_content)
            
    except Exception as e:
        print(f"Error processing article {i+1} for CSV: {str(e)}")

# Write to CSV with only the requested columns and limit to 2 posts per day per platform
with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
    # Define CSV headers as requested
    fieldnames = ['Date', 'Platform', 'Content']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    # Write header
    writer.writeheader()
    
    # Process content by date and platform
    for (date, platform), contents in content_by_date_platform.items():
        # Remove duplicates
        unique_contents = []
        for content in contents:
            if content not in unique_contents:
                unique_contents.append(content)
        
        # Limit to 2 posts per day per platform
        for content in unique_contents[:2]:
            writer.writerow({
                'Date': date,
                'Platform': platform,
                'Content': content
            })

print(f"Final CSV file for Google Sheets created: {csv_filename}")
print(f"Format includes only Date, Platform, Content columns")
print(f"Duplicates removed and limited to 2 posts per day per platform")
