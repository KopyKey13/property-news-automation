#!/usr/bin/env python3
import os
import io
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import time
import glob

# Get today's date
today = datetime.now().strftime('%Y-%m-%d')

def direct_image_solution():
    try:
        print("Starting direct image solution...")
        
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
        
        # Check if images directory exists
        if not os.path.exists('images'):
            print("Images directory not found. Creating sample images...")
            os.makedirs('images', exist_ok=True)
            
            # Create a sample image if none exist
            if not os.listdir('images'):
                from PIL import Image, ImageDraw, ImageFont
                for i in range(min(6, len(df))):
                    img = Image.new('RGB', (800, 400), color=(73, 109, 137))
                    d = ImageDraw.Draw(img)
                    d.text((10,10), f"Property News Image {i+1}", fill=(255,255,0))
                    img.save(f'images/sample_image_{i+1}.jpg')
        
        # Upload all images from images directory
        image_urls = []
        image_files = sorted(os.listdir('images'))
        
        if not image_files:
            print("No images found in images directory!")
            return
            
        print(f"Found {len(image_files)} images to upload")
        
        for filename in image_files:
            if filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                file_path = os.path.join('images', filename)
                
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
                image_urls.append(download_url)
                print(f"Uploaded {filename} to Google Drive: {download_url}")
        
        # Ensure we have at least one image
        if not image_urls:
            print("No images were uploaded successfully!")
            return
            
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
        
        # Find or add DriveImageURL column
        if 'DriveImageURL' not in headers:
            headers.append('DriveImageURL')
            drive_image_col = len(headers) - 1
        else:
            drive_image_col = headers.index('DriveImageURL')
            
        # Find or add LastUpdated column
        if 'LastUpdated' not in headers:
            headers.append('LastUpdated')
            last_updated_col = len(headers) - 1
        else:
            last_updated_col = headers.index('LastUpdated')
            
        # Update header row
        sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body={'values': [headers]}
        ).execute()
        
        # Prepare data rows with image URLs
        data_rows = []
        for i, row in enumerate(values[1:], 1):  # Skip header row
            # Extend row if needed to match header length
            while len(row) < len(headers):
                row.append('')
                
            # Assign image URL (cycling through available images)
            row[drive_image_col] = image_urls[i % len(image_urls)]
            
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
            
            print(f"Updated row {i} with image URL and timestamp")
            time.sleep(0.5)  # Small delay between updates
            
        print(f"Successfully updated {len(data_rows)} rows with image URLs")
        
        # Create a trigger file for Zapier
        with open('exports/upload_complete.txt', 'w') as f:
            f.write(f"Upload completed at {datetime.now().isoformat()}")
            
        print("Direct image solution completed successfully!")
        
    except Exception as e:
        print(f"Error in direct_image_solution: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    direct_image_solution()
