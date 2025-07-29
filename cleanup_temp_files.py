# --- FILE: cleanup_temp_files.py ---

import os
import shutil
import time

def cleanup_old_files():
    """
    Deletes subdirectories and zip files in the temp_files folder
    that are older than a specified age.
    """
    # The directory where all temporary job folders and zips are stored
    temp_dir = "/home/mtobasstool/pdf_processor_app/temp_files" # <-- IMPORTANT: Use your username

    # Age threshold in seconds. 3600 seconds = 1 hour.
    # For testing, you could set this to 300 (5 minutes).
    # For production, 3600 (1 hour) or 86400 (24 hours) is better.
    MAX_AGE_SECONDS = 3600 
    
    # Get the current time
    now = time.time()
    
    print(f"Starting cleanup of '{temp_dir}'...")

    if not os.path.exists(temp_dir):
        print("Temp directory not found. Nothing to do.")
        return

    # Loop through all the items in the temporary directory
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        
        try:
            # Get the last modification time of the file/folder
            file_mod_time = os.path.getmtime(file_path)
            
            # Check if the file is older than our max age
            if now - file_mod_time > MAX_AGE_SECONDS:
                if os.path.isdir(file_path):
                    # If it's a directory, delete it and everything inside
                    shutil.rmtree(file_path)
                    print(f"Deleted old directory: {filename}")
                elif os.path.isfile(file_path) and filename.endswith('.zip'):
                    # If it's a zip file, delete it
                    os.remove(file_path)
                    print(f"Deleted old zip file: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup_old_files()