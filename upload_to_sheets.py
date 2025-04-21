#!/usr/bin/env python3
import os
import json
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime

# Get credentials from environment
credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
sheet_id = os.environ.get('GOOGLE_SHEET_ID')

# Path to the CSV file
today = datetime.now().strftime('%Y-%m-%d')
csv_path = f'exports/property_news_social_content_with_images_{today}.csv'

def upload_to_sheets():
    # Load credentials
    credentials_info = json.loads(credentials_json)
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, 
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    
    # Build the Sheets API service
    service = build('sheets', 'v4', credentials=credentials)
    
    # Read the CSV file
    df = pd.read_csv(csv_path)
    
    # Convert DataFrame to values list
    values = [df.columns.tolist()] + df.values.tolist()
    
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

if __name__ == "__main__":
    upload_to_sheets()
