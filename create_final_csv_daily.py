#!/usr/bin/env python3
import os
import json
import csv
from datetime import datetime

# Create directories if they don't exist
os.makedirs('exports', exist_ok=True)

def create_final_csv():
    """Create a final CSV file with Date, Platform, Content columns."""
    today = datetime.now().strftime('%Y-%m-%d')
    input_file = f'formatted/social_content_{today}.json'
    output_file = f'exports/property_news_social_content_final_{today}.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return
    
    # Load the JSON data
    with open(input_file, 'r') as f:
        posts = json.load(f)
    
    # Create the CSV file with only the required columns
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Platform', 'Content'])
        
        for post in posts:
            writer.writerow([
                post['date'],
                post['platform'],
                post['content']
            ])
    
    print(f"Created final CSV file with {len(posts)} posts: {output_file}")
    return output_file

if __name__ == "__main__":
    create_final_csv()
