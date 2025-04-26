#!/usr/bin/env python3
import os
import json
import io
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import re
import requests
import time
import glob

# Path to the CSV file - look for both possible filenames
today = datetime.now().strftime('%Y-%m-%d')
csv_path_filtered = f'exports/property_news_social_content_filtered_{today}.csv'
csv_path_final = f'exports/property_news_social_content_final_{today}.csv'

# Use the filtered CSV if it exists, otherwise use the final CSV
csv_path = csv_path_filtered if os.path.exists(csv_path_filtered) else csv_path_final

def upload_to_google_drive():
    try:
        # Create credentials file from secret
        credentials_file = 'credentials.json'
        
        # Check if credentials file exists (created in GitHub Actions workflow)
        if not os.path.exists(credentials_file):
            print(f"Credentials file not found: {credentials_file}")
            print("This script expects credentials to be stored in a file.")
            return {}
        
        # Load credentials from file
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # Build the Drive API service
        drive_service = build('drive', 'v3', credentials=credentials)
        
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
            print(f"Made folder publicly accessible")
        else:
            folder_id = items[0]['id']
            print(f"Found existing Google Drive folder: {folder_name} (ID: {folder_id})")
        
        # Dictionary to store image paths and their Google Drive URLs
        image_urls = {}
        
        # Upload images from the images directory
        if os.path.exists('images'):
            image_files = os.listdir('images')
            if not image_files:
                print("Warning: 'images' directory exists but is empty. No images to upload.")
            else:
                print(f"Found {len(image_files)} files in images directory")
            
            for filename in image_files:
                if filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                    file_path = os.path.join('images', filename)
                    
                    # Check if file exists
                    if not os.path.exists(file_path):
                        print(f"Image file not found: {file_path}")
                        continue
                    
                    # Upload file to Google Drive
                    file_metadata = {
                        'name': filename,
                        'parents': [folder_id]
                    }
                    
                    with open(file_path, 'rb') as f:
                        media = MediaIoBaseUpload(io.BytesIO(f.read()), 
                                                 mimetype='image/jpeg',
                                                 resumable=True)
                        file = drive_service.files().create(body=file_metadata,
                                                          media_body=media,
                                                          fields='id,webViewLink').execute()
                    
                    # Make file publicly accessible
                    permission = {
                        'type': 'anyone',
                        'role': 'reader'
                    }
                    drive_service.permissions().create(fileId=file.get('id'), body=permission).execute()
                    
                    # Get direct download link
                    file_id = file.get('id')
                    download_url = f"https://drive.google.com/uc?export=view&id={file_id}"
                    
                    # Store the mapping from local path to Google Drive URL
                    # Store multiple variations of the path to increase matching chances
                    image_urls[f'images/{filename}'] = download_url
                    image_urls[filename] = download_url
                    image_urls[file_path] = download_url
                    
                    # Also store a version with the article ID pattern
                    if re.match(r'article_\d+', filename):
                        article_id = re.search(r'article_(\d+)', filename).group(1)
                        image_urls[f'article_{article_id}'] = download_url
                    
                    print(f"Uploaded {filename} to Google Drive: {download_url}")
        else:
            print("Warning: 'images' directory does not exist. No images to upload.")
        
        # Print all image URLs for debugging
        print("\nAll image URLs:")
        for path, url in image_urls.items():
            print(f"  {path} -> {url}")
        
        return image_urls
    
    except Exception as e:
        print(f"Error in upload_to_google_drive: {str(e)}")
        return {}

def upload_to_sheets_sequential(image_urls):
    try:
        # Create credentials file from secret
        credentials_file = 'credentials.json'
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        
        if not sheet_id:
            print("Error: GOOGLE_SHEET_ID environment variable not found.")
            print("Please set this in your GitHub Secrets.")
            return
        
        # Check if credentials file exists (created in GitHub Actions workflow)
        if not os.path.exists(credentials_file):
            print(f"Credentials file not found: {credentials_file}")
            print("This script expects credentials to be stored in a file.")
            return
        
        # Load credentials from file
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Build the Sheets API service
        service = build('sheets', 'v4', credentials=credentials)
        
        # Check if CSV file exists
        if not csv_path or not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            print("Available files in exports directory:")
            if os.path.exists('exports'):
                print(os.listdir('exports'))
            else:
                print("Exports directory does not exist")
            return
        
        print(f"Using CSV file: {csv_path}")
        
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Check if we have any rows to upload
        if len(df) == 0:
            print("No new content to upload to Google Sheet. CSV file is empty.")
            return
        
        # Print CSV columns for debugging
        print(f"CSV columns: {df.columns.tolist()}")
        
        # Add ImagePath column if it doesn't exist
        if 'ImagePath' not in df.columns:
            print("ImagePath column not found in CSV. Creating empty column.")
            df['ImagePath'] = ""
        
        # Print first few rows of ImagePath for debugging
        print("\nFirst few ImagePath values:")
        for i, path in enumerate(df['ImagePath'].head(5)):
            print(f"  Row {i+1}: '{path}'")
        
        # Add a dedicated DriveImageURL column with Google Drive URLs
        if 'ImagePath' in df.columns:
            # Function to convert local path to Google Drive URL with flexible matching
            def convert_to_drive_url(path):
                if pd.isna(path) or not path:
                    # If no path, try to match based on row index
                    return ""
                
                # Try different variations of the path
                path_variations = []
                
                # Original path
                path_variations.append(path)
                
                # Extract just the filename part if it's a path
                if '/' in path:
                    filename = os.path.basename(path)
                    path_variations.append(filename)
                    
                    # Make sure we're only using the path relative to the repo root
                    clean_path = re.sub(r'^.*?images/', 'images/', path)
                    path_variations.append(clean_path)
                
                # If path contains article ID, extract it
                if 'article_' in path:
                    article_id_match = re.search(r'article_(\d+)', path)
                    if article_id_match:
                        article_id = article_id_match.group(1)
                        path_variations.append(f'article_{article_id}')
                
                # Print all variations for debugging
                print(f"Path variations for '{path}':")
                for var in path_variations:
                    print(f"  - '{var}' -> {var in image_urls}")
                
                # Try to find a match in image_urls
                for var in path_variations:
                    if var in image_urls:
                        return image_urls[var]
                
                # If no match found, try a more flexible approach with partial matching
                for key in image_urls:
                    for var in path_variations:
                        if var in key or key in var:
                            print(f"Partial match: '{var}' in '{key}'")
                            return image_urls[key]
                
                # If still no match, try matching by article ID pattern
                for key in image_urls:
                    if 'article_' in key and 'article_' in path:
                        key_id = re.search(r'article_(\d+)', key)
                        path_id = re.search(r'article_(\d+)', path)
                        if key_id and path_id and key_id.group(1) == path_id.group(1):
                            print(f"Article ID match: '{path}' with '{key}'")
                            return image_urls[key]
                
                # If we have image URLs but no match, use the first one as a fallback
                if image_urls and len(df) > 0:
                    # Assign images sequentially if we have multiple
                    row_index = df[df['ImagePath'] == path].index[0] if not df[df['ImagePath'] == path].empty else 0
                    image_keys = list(image_urls.keys())
                    if row_index < len(image_keys):
                        fallback_key = image_keys[row_index % len(image_keys)]
                        print(f"Using fallback image for row {row_index+1}: {fallback_key}")
                        return image_urls[fallback_key]
                    elif image_keys:
                        fallback_key = image_keys[0]
                        print(f"Using first image as fallback: {fallback_key}")
                        return image_urls[fallback_key]
                
                print(f"No match found for '{path}'")
                return ""
            
            # Create a new DriveImageURL column with the Google Drive URLs
            print("\nGenerating DriveImageURL values...")
            df['DriveImageURL'] = df['ImagePath'].apply(convert_to_drive_url)
            
            # Keep the original ImagePath column for reference
            # But also update it to use relative paths consistently
            df['ImagePath'] = df['ImagePath'].apply(lambda x: re.sub(r'^.*?images/', 'images/', x) if pd.notna(x) and x and '/' in x else x)
            
            # Print some examples for debugging
            print("\nAdded DriveImageURL column with examples:")
            for i, (path, url) in enumerate(zip(df['ImagePath'].head(5), df['DriveImageURL'].head(5))):
                print(f"  Row {i+1}: '{path}' -> '{url}'")
        
        # Add LastUpdated column if it doesn't exist
        if 'LastUpdated' not in df.columns:
            df['LastUpdated'] = ""
        
        # Add Date column with today's date if it doesn't exist
        if 'Date' not in df.columns:
            df['Date'] = today
        else:
            # Update all dates to today
            df['Date'] = today
        
        # Clean the data to remove problematic characters and formatting
        for col in df.columns:
            if df[col].dtype == 'object':  # Only process string columns
                # Replace newlines with spaces
                df[col] = df[col].str.replace('\n', ' ').str.replace('\r', ' ')
                # Replace quotes with single quotes to avoid JSON issues
                df[col] = df[col].str.replace('"', "'")
                # Truncate long content to avoid API limits
                df[col] = df[col].str.slice(0, 40000)
        
        # Get current data from Google Sheet to determine where to append
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='Sheet1'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            print("No data found in Google Sheet. Starting with a fresh sheet.")
            start_row = 1
            headers = df.columns.tolist()
        else:
            headers = values[0]
            start_row = len(values) + 1
            print(f"Found {len(values)-1} existing rows in Google Sheet. Will append starting at row {start_row}.")
            
            # Check if headers match
            if set(df.columns) != set(headers):
                print("Warning: CSV columns don't match Google Sheet headers.")
                print(f"CSV columns: {df.columns.tolist()}")
                print(f"Sheet headers: {headers}")
                
                # Add missing columns to DataFrame
                for header in headers:
                    if header not in df.columns:
                        df[header] = ""
                
                # Reorder columns to match sheet headers
                df = df[headers]
        
        # If sheet is empty, add headers
        if start_row == 1:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='Sheet1!A1',
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
            start_row = 2  # Start data at row 2
            print(f"Added header row to Google Sheet")
        
        # Update each row individually with a delay
        for i, row in enumerate(df.to_dict('records')):
            # Add LastUpdated timestamp with a slight offset for each row
            # This ensures Zapier sees each row as updated at a different time
            timestamp = datetime.now().isoformat()
            row['LastUpdated'] = timestamp
            
            # Convert row to list with proper handling for NaN values
            row_values = [['' if pd.isna(val) else str(val) for val in [row.get(col, '') for col in headers]]]
            
            # Update this specific row
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=f'Sheet1!A{start_row + i}',
                valueInputOption='RAW',
                body={'values': row_values}
            ).execute()
            
            print(f"Added row {start_row + i} with timestamp {timestamp}")
            
            # Add a small delay between updates (0.5 seconds)
            time.sleep(0.5)
        
        print(f"Successfully uploaded {len(df)} new rows to Google Sheet: {sheet_id} using sequential updates")
        
        # Create a trigger file for Zapier
        with open('exports/upload_complete.txt', 'w') as f:
            f.write(f"Upload completed at {datetime.now().isoformat()}")
            
    except Exception as e:
        print(f"Error in upload_to_sheets_sequential: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # First upload images to Google Drive
    image_urls = upload_to_google_drive()
    
    # Then update Google Sheets with the Google Drive URLs using sequential updates
    upload_to_sheets_sequential(image_urls)
