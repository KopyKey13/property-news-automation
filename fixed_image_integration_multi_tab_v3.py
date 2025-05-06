"""
This script is responsible for ensuring images exist for posts, uploading them to Google Drive,
and then updating a Google Sheet with the post details and Drive image URLs.
It now writes to platform-specific tabs in the Google Sheet for better Zapier integration
and includes a fix to handle NaN values before uploading to Google Sheets.
"""
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
import random

# Path to the CSV file - look for both possible filenames
today = datetime.now().strftime("%Y-%m-%d")
# Use the V2 CSV which includes the Title column for better Zapier mapping
csv_path = f"exports/property_news_social_content_final_v2_{today}.csv"


# Unsplash API for fallback images if needed
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")

# More specific keywords, prioritized
PRIMARY_PROPERTY_KEYWORDS = [
    "HMO", "Rent-to-Rent", "BRRR", "Serviced Accommodation", "property investment",
    "real estate investment", "buy-to-let", "property development", "housing market",
    "property portfolio", "landlord", "tenant", "lettings", "estate agent",
    "mortgage rates", "property tax", "stamp duty", "capital gains tax",
    "modern interior", "luxury home", "apartment living", "house design",
    "kitchen design", "living room decor", "bedroom design", "garden design",
    "uk property", "london property", "manchester property", "birmingham property"
]
SECONDARY_PROPERTY_KEYWORDS = [
    "property", "real estate", "house", "home", "apartment", "building", "investment", "market"
]

def get_unsplash_image(keywords_for_query):
    """Get an image from Unsplash API using a list of keywords."""
    if not UNSPLASH_ACCESS_KEY:
        print("Warning: UNSPLASH_ACCESS_KEY not set. Cannot fetch Unsplash image.")
        return None, None
    
    if not keywords_for_query:
        print("Warning: No keywords provided for Unsplash query. Using a default keyword.")
        query = random.choice(PRIMARY_PROPERTY_KEYWORDS)
    else:
        query = " ".join(random.sample(keywords_for_query, min(len(keywords_for_query), 3)))

    print(f"Searching Unsplash for: {query}")
    
    try:
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape&content_filter=high"
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            image_url = data["urls"]["regular"]
            attribution = f"Photo by {data['user']['name']} on Unsplash"
            return image_url, attribution
        else:
            print(f"Error from Unsplash API: {response.status_code} - {response.text}")
            if len(keywords_for_query) > 1:
                print("Retrying with a broader query...")
                return get_unsplash_image([random.choice(keywords_for_query)])
            return None, None
    except Exception as e:
        print(f"Error getting Unsplash image: {str(e)}")
        return None, None

def download_image(url, filename):
    """Download an image from a URL."""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        else:
            print(f"Error downloading image: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error downloading image: {str(e)}")
        return False

def extract_keywords_from_content(content, title=""):
    """Extract relevant keywords from post content and title for image search."""
    text_to_search = f"{title.lower()} {content.lower()}"
    extracted_keywords = []
    for keyword in PRIMARY_PROPERTY_KEYWORDS:
        if keyword.lower() in text_to_search:
            extracted_keywords.append(keyword)
    if len(extracted_keywords) < 3:
        for keyword in SECONDARY_PROPERTY_KEYWORDS:
            if keyword.lower() in text_to_search and keyword not in extracted_keywords:
                extracted_keywords.append(keyword)
                if len(extracted_keywords) >= 5:
                    break
    if not extracted_keywords:
        extracted_keywords = random.sample(PRIMARY_PROPERTY_KEYWORDS, 3)
    return list(set(extracted_keywords))

def ensure_images_for_all_posts():
    """Ensure we have images for all posts in the CSV file."""
    if not os.path.exists(csv_path):
        print(f"CSV file not found: {csv_path}")
        return pd.DataFrame() # Return empty DataFrame
    
    os.makedirs("images", exist_ok=True)
    df = pd.read_csv(csv_path)
    if df.empty:
        print("No posts found in CSV file.")
        return df

    if "ImagePath" not in df.columns:
        df["ImagePath"] = ""
    if "ImageAttribution" not in df.columns:
        df["ImageAttribution"] = ""

    for i, row in df.iterrows():
        content = str(row.get("Content", ""))
        title = str(row.get("Title", "")) 
        image_path = str(row.get("ImagePath", ""))

        if not image_path or not os.path.exists(image_path):
            print(f"No existing image for row {i+1} (Title: {title[:30]}...), fetching new one.")
            keywords = extract_keywords_from_content(content, title)
            print(f"Keywords for Unsplash query: {keywords}")
            image_url, attribution = get_unsplash_image(keywords)
            if image_url and attribution:
                filename = f"images/article_{i+1}_{today}_{random.randint(1000,9999)}.jpg"
                if download_image(image_url, filename):
                    df.at[i, "ImagePath"] = filename
                    df.at[i, "ImageAttribution"] = attribution
                    print(f"Downloaded new image for row {i+1}: {filename} with attribution: {attribution}")
                else:
                    print(f"Failed to download image for row {i+1}")
            else:
                print(f"Could not get image from Unsplash for row {i+1} using keywords: {keywords}")
        else:
            print(f"Using existing image for row {i+1}: {image_path}")
    
    df.to_csv(csv_path, index=False)
    print(f"Ensured images for all {len(df)} posts in CSV file.")
    return df

def upload_to_google_drive(df_with_images):
    """Uploads images referenced in the DataFrame to Google Drive and returns a map of local paths to Drive URLs."""
    try:
        credentials_file = "credentials.json"
        if not os.path.exists(credentials_file):
            print(f"Credentials file not found: {credentials_file}")
            return {}
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, 
            scopes=["https://www.googleapis.com/auth/drive"])
        drive_service = build("drive", "v3", credentials=credentials)
        
        folder_name = f"property_news_images_{today}"
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query).execute()
        items = results.get("files", [])
        
        if not items:
            folder_metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
            folder = drive_service.files().create(body=folder_metadata, fields="id").execute()
            folder_id = folder.get("id")
            permission = {"type": "anyone", "role": "reader"}
            drive_service.permissions().create(fileId=folder_id, body=permission).execute()
            print(f"Created and shared Google Drive folder: {folder_name} (ID: {folder_id})")
        else:
            folder_id = items[0]["id"]
            print(f"Found existing Google Drive folder: {folder_name} (ID: {folder_id})")
        
        uploaded_image_urls = {}
        for index, row in df_with_images.iterrows():
            local_image_path = str(row.get("ImagePath", ""))
            if not local_image_path or not os.path.exists(local_image_path):
                print(f"Image path missing or file does not exist for row {index+1}: '{local_image_path}'. Skipping upload.")
                continue

            filename = os.path.basename(local_image_path)
            file_metadata = {"name": filename, "parents": [folder_id]}
            with open(local_image_path, "rb") as f:
                media = MediaIoBaseUpload(io.BytesIO(f.read()), mimetype="image/jpeg", resumable=True)
                file = drive_service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()
            
            permission = {"type": "anyone", "role": "reader"}
            drive_service.permissions().create(fileId=file.get("id"), body=permission).execute()
            file_id = file.get("id")
            download_url = f"https://drive.google.com/uc?export=view&id={file_id}"
            
            uploaded_image_urls[local_image_path] = download_url
            print(f"Uploaded {filename} (from {local_image_path}) to Google Drive: {download_url}")

        print("\nAll uploaded image URLs mapping local path to Drive URL:")
        for path, url in uploaded_image_urls.items():
            print(f"  {path} -> {url}")
        return uploaded_image_urls
    except Exception as e:
        print(f"Error in upload_to_google_drive: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

def upload_to_sheets_multi_tab(df_with_drive_urls):
    try:
        credentials_file = "credentials.json"
        sheet_id = os.environ.get("GOOGLE_SHEET_ID")
        if not sheet_id or not os.path.exists(credentials_file):
            print("Missing Google Sheet ID or credentials file.")
            return

        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        service = build("sheets", "v4", credentials=credentials)

        if df_with_drive_urls.empty:
            print("No new content to upload to Google Sheets.")
            return

        print(f"Preparing to upload {len(df_with_drive_urls)} rows to Google Sheets using multi-tab approach.")

        # Standardize Date and LastUpdated columns
        df_with_drive_urls["Date"] = today
        if "LastUpdated" not in df_with_drive_urls.columns:
            df_with_drive_urls["LastUpdated"] = ""

        # Ensure all expected columns are present, add if missing
        expected_headers = ["Date", "Platform", "Title", "Content", "ImagePath", "ImageAttribution", "DriveImageURL", "LastUpdated"]
        for header in expected_headers:
            if header not in df_with_drive_urls.columns:
                df_with_drive_urls[header] = "" # Add missing column with empty values
        
        # Reorder columns to the expected order
        df_with_drive_urls = df_with_drive_urls[expected_headers]

        # Clean data for Sheets API - This was already here, but NaN handling needs to be more robust
        # Convert all columns to string and replace NaN with empty string BEFORE this step for safety
        df_with_drive_urls = df_with_drive_urls.fillna('') # Fill NaN across the entire DataFrame
        for col in df_with_drive_urls.columns:
            # Ensure all data is string type before further processing
            df_with_drive_urls[col] = df_with_drive_urls[col].astype(str)
            if df_with_drive_urls[col].dtype == "object": # Redundant check now, but keep for safety
                df_with_drive_urls[col] = df_with_drive_urls[col].str.replace("\n|\r", " ", regex=True).str.replace('"', '""', regex=False).str.slice(0, 40000)

        platforms = df_with_drive_urls["Platform"].unique()
        for platform_name in platforms:
            platform_df = df_with_drive_urls[df_with_drive_urls["Platform"] == platform_name].copy()
            if platform_df.empty:
                print(f"No posts for platform: {platform_name}")
                continue
            
            # This line was added in thought process, but applying fillna to df_with_drive_urls earlier is better.
            # platform_df.fillna('', inplace=True) # Ensure NaNs are handled for this specific platform's data

            sheet_name = f"{platform_name}_Posts"
            print(f"Processing sheet: {sheet_name} for {len(platform_df)} posts")

            try:
                sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
                sheets = [s["properties"]["title"] for s in sheet_metadata.get("sheets", [])]
                if sheet_name not in sheets:
                    body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
                    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()
                    print(f"Created new sheet: {sheet_name}")
                    service.spreadsheets().values().update(
                        spreadsheetId=sheet_id, range=f"{sheet_name}!A1", valueInputOption="RAW", 
                        body={"values": [expected_headers]}).execute()
                    print(f"Added headers to {sheet_name}")

                result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{sheet_name}!A:A").execute()
                values = result.get("values", [])
                start_row = len(values) + 1
                
                if start_row == 1 and sheet_name not in sheets:
                     service.spreadsheets().values().update(
                        spreadsheetId=sheet_id, range=f"{sheet_name}!A1", valueInputOption="RAW", 
                        body={"values": [expected_headers]}).execute()
                     print(f"Added headers to {sheet_name} (first time)")
                     start_row = 2
                elif start_row == 1 and sheet_name in sheets and not values:
                    service.spreadsheets().values().update(
                        spreadsheetId=sheet_id, range=f"{sheet_name}!A1", valueInputOption="RAW", 
                        body={"values": [expected_headers]}).execute()
                    print(f"Added headers to empty existing sheet: {sheet_name}")
                    start_row = 2

                print(f"Appending {len(platform_df)} rows to {sheet_name} starting at row {start_row}")

                for i, record_tuple in enumerate(platform_df.iterrows()):
                    index, record = record_tuple
                    timestamp = datetime.now().isoformat()
                    # Update LastUpdated in the platform_df (which is a copy)
                    platform_df.loc[index, "LastUpdated"] = timestamp
                    
                    # Construct row_values, ensuring all are strings and NaN is handled (already done by fillna and astype(str) earlier)
                    current_row_data = [platform_df.loc[index, col] for col in expected_headers]
                    row_values = [current_row_data]
                    
                    service.spreadsheets().values().update(
                        spreadsheetId=sheet_id, range=f"{sheet_name}!A{start_row + i}", 
                        valueInputOption="RAW", body={"values": row_values}).execute()
                    print(f"Added row {start_row + i} to {sheet_name} with timestamp {timestamp}")
                    time.sleep(0.5)
                print(f"Successfully uploaded {len(platform_df)} new rows to {sheet_name}")

            except Exception as e:
                print(f"Error processing sheet {sheet_name}: {str(e)}")
                import traceback
                traceback.print_exc()

        with open("exports/upload_complete_multitab.txt", "w") as f:
            f.write(f"Multi-tab upload completed at {datetime.now().isoformat()}")
            
    except Exception as e:
        print(f"Error in upload_to_sheets_multi_tab: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    df_with_image_paths = ensure_images_for_all_posts()
    
    if not df_with_image_paths.empty:
        drive_urls_map = upload_to_google_drive(df_with_image_paths)
        
        df_for_sheets = df_with_image_paths.copy()
        if "DriveImageURL" not in df_for_sheets.columns:
            df_for_sheets["DriveImageURL"] = ""

        for index, row in df_for_sheets.iterrows():
            local_path = str(row.get("ImagePath", ""))
            if local_path in drive_urls_map:
                df_for_sheets.loc[index, "DriveImageURL"] = drive_urls_map[local_path]
            else:
                # If image wasn't uploaded (e.g. path error), ensure DriveImageURL is empty or has a placeholder
                df_for_sheets.loc[index, "DriveImageURL"] = "" 
        
        upload_to_sheets_multi_tab(df_for_sheets)
    else:
        print("No content to process for Google Sheets upload.")

