#!/usr/bin/env python3
import os
import json
import io
import pandas as pd
import re
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import time
import glob

# Get today's date
today = datetime.now().strftime('%Y-%m-%d')

# Get Unsplash API key from environment variable
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")

def extract_keywords(text):
    """Extract relevant keywords from text for image search."""
    if not text:
        return ["property", "real estate"]
    
    # Property-related keywords to look for
    property_keywords = [
        "property", "house", "home", "real estate", "apartment", "mortgage", 
        "landlord", "tenant", "rent", "housing", "market", "investment",
        "building", "development", "commercial", "residential", "office"
    ]
    
    # Clean the text
    text_lower = text.lower()
    
    # Extract property-related keywords that appear in the text
    found_keywords = []
    for keyword in property_keywords:
        if keyword in text_lower and keyword not in found_keywords:
            found_keywords.append(keyword)
    
    # If no property keywords found, extract some words from the text
    if not found_keywords:
        # Remove common words and extract key terms
        common_words = ['the', 'and', 'to', 'of', 'in', 'on', 'with', 'for', 'a', 'is', 'are', 'that', 'this']
        words = re.findall(r'\b\w+\b', text_lower)
        meaningful_words = [word for word in words if word not in common_words and len(word) > 3]
        found_keywords = meaningful_words[:3]  # Take up to 3 meaningful words
    
    # Ensure we have at least one keyword
    if not found_keywords:
        found_keywords = ["property", "real estate"]
    
    return found_keywords[:3]  # Limit to top 3 keywords

def get_unsplash_image(keywords, article_id):
    """Get a relevant image from Unsplash based on keywords."""
    # Skip if no API key is available
    if not UNSPLASH_ACCESS_KEY:
        print(f"No Unsplash API key available for article {article_id}")
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
            
            # Ensure images directory exists
            os.makedirs('images', exist_ok=True)
            
            with open(img_filename, 'wb') as img_file:
                img_file.write(img_response.content)
            
            print(f"Downloaded relevant image for article {article_id} with keywords {keywords}")
            
            return {
                'filename': img_filename,
                'url': image_url,
                'photographer': photographer,
                'attribution': f"Photo by {photographer} on Unsplash"
            }
        else:
            print(f"No Unsplash results for article {article_id} with keywords {keywords}")
            return None
    except Exception as e:
        print(f"Error fetching image from Unsplash for article {article_id}: {str(e)}")
        return None

def create_fallback_image(article_id, keywords):
    """Create a fallback image with text if Unsplash fails."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Ensure images directory exists
        os.makedirs('images', exist_ok=True)
        
        # Create a simple image with text
        img_filename = f"images/fallback_article_{article_id:02d}.jpg"
        
        # Create image with gradient background
        img = Image.new('RGB', (800, 400), color=(73, 109, 137))
        d = ImageDraw.Draw(img)
        
        # Try to load a font, use default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 36)
            small_font = ImageFont.truetype("arial.ttf", 24)
        except IOError:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add text to image
        keyword_text = ", ".join(keywords)
        d.text((50, 50), f"Property News", fill=(255, 255, 255), font=font)
        d.text((50, 120), f"Keywords: {keyword_text}", fill=(255, 255, 200), font=small_font)
        d.text((50, 300), f"Article {article_id}", fill=(200, 200, 255), font=small_font)
        
        img.save(img_filename)
        
        print(f"Created fallback image for article {article_id}")
        
        return {
            'filename': img_filename,
            'url': '',
            'photographer': 'System Generated',
            'attribution': 'Fallback image generated by system'
        }
    except Exception as e:
        print(f"Error creating fallback image for article {article_id}: {str(e)}")
        return None

def relevant_image_solution():
    try:
        print("Starting relevant image solution...")
        
        # Create credentials file from secret
        credentials_file = 'credentials.json'
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        
        if not sheet_id:
            print("Error: GOOGLE_SHEET_ID environment variable not found.")
            return
        
        # Check if credentials file exists
        if not os.path.exists(credentials_file):
            print(f"Credentials file not found: {credentials_file}")
            return
        
        # Load credentials from file
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Build the Drive API service
        drive_service = build('drive', 'v3', credentials=credentials)
        sheets_service = build('sheets', 'v4', credentials=credentials)
        
        # Create a folder for today's property news images
        folder_name = f'property_news_images_{today}'
        folder_id = None
        
        # Check if folder already exists
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query).execute()
        items = results.get('files', [])
        
        if not items:
            # Create folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"Created Google Drive folder: {folder_name} (ID: {folder_id})")
            
            # Make folder publicly accessible
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            drive_service.permissions().create(fileId=folder_id, body=permission).execute()
        else:
            folder_id = items[0]['id']
            print(f"Found existing Google Drive folder: {folder_name} (ID: {folder_id})")
        
        # Find any CSV file in exports directory
        csv_files = glob.glob('exports/*.csv')
        if not csv_files:
            print("No CSV files found in exports directory!")
            return
        
        csv_path = csv_files[0]
        print(f"Using CSV file: {csv_path}")
        
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Print CSV columns for debugging
        print(f"CSV columns: {df.columns.tolist()}")
        
        # Get current data from Google Sheet
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='Sheet1'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print("No data found in Google Sheet!")
            return
            
        # Get headers
        headers = values[0]
        
        # Find or add necessary columns
        if 'DriveImageURL' not in headers:
            headers.append('DriveImageURL')
        drive_image_col = headers.index('DriveImageURL')
            
        if 'ImageAttribution' not in headers:
            headers.append('ImageAttribution')
        image_attribution_col = headers.index('ImageAttribution')
            
        if 'LastUpdated' not in headers:
            headers.append('LastUpdated')
        last_updated_col = headers.index('LastUpdated')
        
        # Find Content column
        content_col = headers.index('Content') if 'Content' in headers else None
        if content_col is None:
            print("Warning: Content column not found in Google Sheet!")
            # Try to find any column that might contain content
            for i, header in enumerate(headers):
                if 'content' in header.lower() or 'text' in header.lower() or 'post' in header.lower():
                    content_col = i
                    print(f"Using {header} column for content")
                    break
            
            if content_col is None:
                print("No suitable content column found. Using first non-header row for keywords.")
                content_col = 1  # Default to second column if no content column found
        
        # Update header row
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body={'values': [headers]}
        ).execute()
        
        # Process each row
        data_rows = []
        for i, row in enumerate(values[1:], 1):  # Skip header row
            # Extend row if needed to match header length
            while len(row) < len(headers):
                row.append('')
            
            # Extract content for keyword generation
            content = row[content_col] if content_col < len(row) else ""
            
            # Extract keywords from content
            keywords = extract_keywords(content)
            print(f"Row {i}: Extracted keywords: {keywords}")
            
            # Get relevant image from Unsplash
            image_info = get_unsplash_image(keywords, i)
            
            # If Unsplash fails, create a fallback image
            if not image_info:
                image_info = create_fallback_image(i, keywords)
            
            # If we have an image, upload it to Google Drive
            if image_info:
                file_path = image_info['filename']
                
                # Upload file to Google Drive
                file_metadata = {
                    'name': os.path.basename(file_path),
                    'parents': [folder_id]
                }
                
                with open(file_path, 'rb') as f:
                    media = MediaIoBaseUpload(io.BytesIO(f.read()), 
                                             mimetype='image/jpeg',
                                             resumable=True)
                    file = drive_service.files().create(body=file_metadata,
                                                      media_body=media,
                                                      fields='id').execute()
                
                # Make file publicly accessible
                permission = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                drive_service.permissions().create(fileId=file.get('id'), body=permission).execute()
                
                # Get direct download link
                file_id = file.get('id')
                download_url = f"https://drive.google.com/uc?export=view&id={file_id}"
                
                # Add image URL and attribution to row
                row[drive_image_col] = download_url
                row[image_attribution_col] = image_info['attribution']
                
                print(f"Uploaded relevant image for row {i} to Google Drive: {download_url}")
            else:
                print(f"Warning: No image available for row {i}")
            
            # Add timestamp
            timestamp = datetime.now().isoformat()
            row[last_updated_col] = timestamp
            
            data_rows.append(row)
            
        # Update each row individually with a delay
        for i, row in enumerate(data_rows, 2):  # Start from row 2 (after header)
            sheets_service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f'Sheet1!A{i}',
                valueInputOption='RAW',
                body={'values': [row]}
            ).execute()
            
            print(f"Updated row {i} with relevant image URL and timestamp")
            time.sleep(0.5)  # Small delay between updates
            
        print(f"Successfully updated {len(data_rows)} rows with relevant image URLs")
        
        # Create a trigger file for Zapier
        with open('exports/upload_complete.txt', 'w') as f:
            f.write(f"Upload completed at {datetime.now().isoformat()}")
            
        print("Relevant image solution completed successfully!")
        
    except Exception as e:
        print(f"Error in relevant_image_solution: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    relevant_image_solution()
