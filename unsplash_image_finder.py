#!/usr/bin/env python3
import json
import csv
import os
import requests
from datetime import datetime
import re

# Create directory for images
os.makedirs('images', exist_ok=True)

# Get Unsplash API key from environment variable (set in GitHub Actions)
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")

# Check if API key is available
if not UNSPLASH_ACCESS_KEY:
    print("Warning: UNSPLASH_ACCESS_KEY environment variable not found.")
    print("Please set it as a GitHub Secret and update your workflow file.")
    print("Continuing with limited functionality...")

# Load the articles
with open('articles/latest_property_news.json', 'r') as f:
    articles = json.load(f)

# Load the CSV file
today = datetime.now().strftime('%Y-%m-%d')
csv_filename = f'exports/property_news_social_content_final_{today}.csv'
updated_csv_filename = f'exports/property_news_social_content_with_images_{today}.csv'

# Function to extract keywords from article title
def extract_keywords(title):
    # Remove common words and extract key property terms
    common_words = ['the', 'and', 'to', 'of', 'in', 'on', 'with', 'for', 'a', 'is', 'are']
    property_keywords = ['property', 'house', 'home', 'real estate', 'apartment', 'mortgage', 
                         'landlord', 'tenant', 'rent', 'housing', 'market']
    
    # Clean the title
    title_lower = title.lower()
    words = re.findall(r'\b\w+\b', title_lower)
    
    # Extract meaningful keywords
    keywords = [word for word in words if word not in common_words and len(word) > 3]
    
    # Add property-related keywords
    for keyword in property_keywords:
        if keyword in title_lower and keyword not in keywords:
            keywords.append(keyword)
    
    # Ensure we have at least one keyword
    if not keywords:
        keywords = ['property', 'real estate']
    
    return keywords[:3]  # Limit to top 3 keywords

# Function to get image from Unsplash
def get_unsplash_image(keywords, article_id):
    # Skip if no API key is available
    if not UNSPLASH_ACCESS_KEY:
        return None
        
    search_query = ' '.join(keywords)
    url = f"https://api.unsplash.com/search/photos?query={search_query}&per_page=1"
    
    headers = {
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'results' in data and len(data['results']) > 0:
            image_url = data['results'][0]['urls']['regular']
            image_id = data['results'][0]['id']
            photographer = data['results'][0]['user']['name']
            
            # Download the image
            img_response = requests.get(image_url)
            img_filename = f"images/article_{article_id:02d}_{image_id}.jpg"
            
            with open(img_filename, 'wb') as img_file:
                img_file.write(img_response.content)
            
            return {
                'filename': img_filename,
                'url': image_url,
                'photographer': photographer,
                'attribution': f"Photo by {photographer} on Unsplash"
            }
        else:
            return None
    except Exception as e:
        print(f"Error fetching image: {str(e)}")
        return None

# Process articles and add images
image_data = {}
for i, article in enumerate(articles[:20]):  # Process first 20 articles
    try:
        # Extract keywords from title
        keywords = extract_keywords(article['title'])
        print(f"Article {i+1}: Keywords: {keywords}")
        
        # Get image from Unsplash
        image_info = get_unsplash_image(keywords, i+1)
        
        if image_info:
            image_data[article['date']] = image_info
            print(f"Added image for article {i+1}: {image_info['filename']}")
        else:
            print(f"No image found for article {i+1}")
            
    except Exception as e:
        print(f"Error processing article {i+1} for images: {str(e)}")

# Update CSV with image information
rows = []
with open(csv_filename, 'r', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    fieldnames = reader.fieldnames + ['ImagePath', 'ImageAttribution']
    
    for row in reader:
        date = row['Date']
        if date in image_data:
            row['ImagePath'] = image_data[date]['filename']
            row['ImageAttribution'] = image_data[date]['attribution']
        else:
            row['ImagePath'] = ''
            row['ImageAttribution'] = ''
        rows.append(row)

# Write updated CSV
with open(updated_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Updated CSV with image information: {updated_csv_filename}")
