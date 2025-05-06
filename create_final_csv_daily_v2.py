#!/usr/bin/env python3
import os
import json
import csv
from datetime import datetime

# Create directories if they don't exist
os.makedirs('exports', exist_ok=True)

def create_final_csv_v2():
    """Create a final CSV file with Date, Platform, Title, and Content columns."""
    today = datetime.now().strftime('%Y-%m-%d')
    input_file = f'formatted/social_content_{today}.json'
    # Output a new version of the CSV to avoid conflicts if old one is expected by other scripts initially
    output_file = f'exports/property_news_social_content_final_v2_{today}.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        # Create an empty CSV with headers if input is missing, so downstream processes don't fail
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Platform', 'Title', 'Content'])
        print(f"Created empty CSV file with headers: {output_file}")
        return output_file
    
    try:
        # Load the JSON data
        with open(input_file, 'r') as f:
            posts = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {input_file}. File might be empty or corrupted.")
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Platform', 'Title', 'Content'])
        print(f"Created empty CSV file with headers: {output_file}")
        return output_file

    if not posts:
        print(f"No posts found in {input_file}. Creating an empty CSV with headers.")
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Platform', 'Title', 'Content'])
        print(f"Created empty CSV file with headers: {output_file}")
        return output_file

    # Create the CSV file with the required columns
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Platform', 'Title', 'Content'])
        
        for post in posts:
            writer.writerow([
                post.get('date', today), # Ensure date is present
                post.get('platform', ''),
                post.get('title', ''), # Add title
                post.get('content', '')
            ])
    
    print(f"Created final CSV file (v2) with {len(posts)} posts: {output_file}")
    return output_file

if __name__ == "__main__":
    create_final_csv_v2()

