#!/usr/bin/env python3
import os
import json
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import re

# Path to the CSV file
today = datetime.now().strftime('%Y-%m-%d')
csv_path = f'exports/property_news_social_content_with_images_{today}.csv'

def upload_to_sheets():
    try:
        # Method 1: Create credentials file from secret
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
        
        # Hardcode GitHub repository information for reliability
        repo_owner = "KopyKey13"
        repo_name = "property-news-automation"
        
        print(f"Using GitHub repository: {repo_owner}/{repo_name}")
        
        # Add a dedicated ImageURL column with GitHub raw URLs
        if 'ImagePath' in df.columns:
            # Function to convert local path to GitHub URL
            def convert_to_github_url(path):
                if pd.isna(path) or not path:
                    return ""
                
                # Extract just the filename part if it's a path
                if '/' in path:
                    # Make sure we're only using the path relative to the repo root
                    path = re.sub(r'^.*?images/', 'images/', path)
                
                return f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/main/{path}"
            
            # Create a new ImageURL column with the GitHub URLs
            df['ImageURL'] = df['ImagePath'].apply(convert_to_github_url)
            
            # Keep the original ImagePath column for reference
            # But also update it to use relative paths consistently
            df['ImagePath'] = df['ImagePath'].apply(lambda x: re.sub(r'^.*?images/', 'images/', x) if pd.notna(x) and x and '/' in x else x)
            
            # Print some examples for debugging
            print("Added ImageURL column with examples:")
            for i, path in enumerate(df['ImageURL'].head(3)):
                print(f"  {i+1}: {path}")
        
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
    upload_to_sheets()
