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

# Path to the CSV file
today = datetime.now().strftime('%Y-%m-%d')
csv_path = f'exports/property_news_social_content_with_images_{today}.csv'

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
        
        # Create a folder for property news images if it doesn't exist
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
            for filename in os.listdir('images'):
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
                    image_urls[f'images/{filename}'] = download_url
                    print(f"Uploaded {filename} to Google Drive: {download_url}")
        
        return image_urls
    
    except Exception as e:
        print(f"Error in upload_to_google_drive: {str(e)}")
        return {}

def upload_to_sheets(image_urls):
    try:
        # Create credentials file from secret
        credentials_file = 'credentials.json'
        sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        
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
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            print("Available files in exports directory:")
            if os.path.exists('exports'):
                print(os.listdir('exports'))
            else:
                print("Exports directory does not exist")
            return
        
        # Read the CSV file
        df = pd.read_csv(csv_path)
        
        # Add a dedicated DriveImageURL column with Google Drive URLs
        if 'ImagePath' in df.columns:
            # Function to convert local path to Google Drive URL
            def convert_to_drive_url(path):
                if pd.isna(path) or not path:
                    return ""
                
                # Extract just the filename part if it's a path
                if '/' in path:
                    # Make sure we're only using the path relative to the repo root
                    path = re.sub(r'^.*?images/', 'images/', path)
                
                # Look up the Google Drive URL for this image
                if path in image_urls:
                    return image_urls[path]
                else:
                    return ""
            
            # Create a new DriveImageURL column with the Google Drive URLs
            df['DriveImageURL'] = df['ImagePath'].apply(convert_to_drive_url)
            
            # Keep the original ImagePath column for reference
            # But also update it to use relative paths consistently
            df['ImagePath'] = df['ImagePath'].apply(lambda x: re.sub(r'^.*?images/', 'images/', x) if pd.notna(x) and x and '/' in x else x)
            
            # Print some examples for debugging
            print("Added DriveImageURL column with examples:")
            for i, path in enumerate(df['DriveImageURL'].head(3)):
                print(f"  {i+1}: {path}")
        
        # Add LastUpdated column to help with Zapier triggers
        df['LastUpdated'] = datetime.now().isoformat()
        print(f"Added LastUpdated column with timestamp: {datetime.now().isoformat()}")
        
        # Clean the data to remove problematic characters and formatting
        for col in df.columns:
            if df[col].dtype == 'object':  # Only process string columns
                # Replace newlines with spaces
                df[col] = df[col].str.replace('\n', ' ').str.replace('\r', ' ')
                # Replace quotes with single quotes to avoid JSON issues
                df[col] = df[col].str.replace('"', "'")
                # Truncate long content to avoid API limits
                df[col] = df[col].str.slice(0, 40000)
        
        # Convert DataFrame to values list - with proper handling for NaN values
        values = [df.columns.tolist()]
        for _, row in df.iterrows():
            # Convert NaN to empty strings and ensure all values are strings
            row_values = ['' if pd.isna(val) else str(val) for val in row]
            values.append(row_values)
        
        # Clear the sheet first
        service.spreadsheets().values().clear(
            spreadsheetId=sheet_id,
            range='Sheet1',
        ).execute()
        
        # Update the sheet with new values
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body={'values': values}
        ).execute()
        
        print(f"Successfully uploaded data to Google Sheet: {sheet_id}")
        
        # Create a trigger file for Zapier
        with open('exports/upload_complete.txt', 'w') as f:
            f.write(f"Upload completed at {datetime.now().isoformat()}")
            
    except Exception as e:
        print(f"Error in upload_to_sheets: {str(e)}")
        # Print environment variables (without revealing full secrets)
        print("Environment variables:")
        for key in os.environ:
            if 'SECRET' in key or 'TOKEN' in key or 'KEY' in key or 'CREDENTIAL' in key:
                print(f"{key}: {'*' * 10}")
            else:
                print(f"{key}: {os.environ[key][:20]}..." if len(os.environ[key]) > 20 else f"{key}: {os.environ[key]}")

if __name__ == "__main__":
    # First upload images to Google Drive
    image_urls = upload_to_google_drive()
    
    # Then update Google Sheets with the Google Drive URLs
    upload_to_sheets(image_urls)
