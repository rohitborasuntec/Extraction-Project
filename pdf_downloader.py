from selenium import webdriver
import os
import pandas as pd
import time
import random  # Import random properly
import shutil

download_dir = os.path.abspath("downloads")
os.makedirs(download_dir, exist_ok=True)

chrome_options = webdriver.ChromeOptions()
prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True,  # forces download instead of opening PDF viewer
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=chrome_options)

df = pd.read_csv(r"d:\Projects\Extraction-Project\debarment_results.csv")

for ind, row in df.iterrows():
    entity_name = row["Name of Entity"]
    
    # Clean the filename: remove invalid characters for Windows filenames
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        entity_name = entity_name.replace(char, '')
    
    # Get list of files before download
    files_before = set(os.listdir(download_dir))
    
    # Navigate to the source link
    driver.get(row["Source Link"])
    time.sleep(random.uniform(5, 8))  # Now this will work
    
    # Wait for a new PDF file to appear
    max_wait = 30  # Maximum seconds to wait for download
    start_time = time.time()
    downloaded_file = None
    
    while time.time() - start_time < max_wait:
        files_after = set(os.listdir(download_dir))
        new_files = files_after - files_before
        
        # Find the newly downloaded PDF file
        for file in new_files:
            if file.lower().endswith('.pdf'):
                downloaded_file = file
                break
        
        if downloaded_file:
            break
        
        time.sleep(1)
    
    # Rename the file if it was downloaded
    if downloaded_file:
        old_path = os.path.join(download_dir, downloaded_file)
        new_path = os.path.join(download_dir, f"{entity_name}.pdf")
        
        # If file with same name exists, add a suffix
        counter = 1
        while os.path.exists(new_path):
            new_path = os.path.join(download_dir, f"{entity_name}_{counter}.pdf")
            counter += 1
        
        # Rename the file
        shutil.move(old_path, new_path)
        print(f"Downloaded and renamed: {downloaded_file} -> {os.path.basename(new_path)}")
    else:
        print(f"No PDF downloaded for {entity_name}")

driver.quit()