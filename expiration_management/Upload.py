import os
import json
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

def upload_photo_to_json_store(source_image_path, storage_dir="storage", json_file="photos.json"):
    os.makedirs(storage_dir, exist_ok=True)
    filename = os.path.basename(source_image_path)
    destination_path = os.path.join(storage_dir, filename)
    
    # Copy file to storage directory
    shutil.copy(source_image_path, destination_path)
    
    metadata = {
        "id": int(datetime.now().timestamp()),
        "filename": filename,
        "filepath": destination_path,
        "file_size_bytes": os.path.getsize(destination_path),
        "upload_time": datetime.now().isoformat()
    }
    
    photos_data = []
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            try:
                photos_data = json.load(f)
            except json.JSONDecodeError:
                photos_data = []
                
    photos_data.append(metadata)
    with open(json_file, "w") as f:
        json.dump(photos_data, f, indent=4)
        
    print(f"\nSuccess! Photo saved to '{destination_path}' and logged in '{json_file}'.")

def select_and_upload_photo():
    # Hide the main Tkinter root window
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)  # Bring file dialog to front

    print("Opening file selector...")
    
    # Open file dialog window filtered for images
    file_path = filedialog.askopenfilename(
        title="Select an Image to Upload",
        filetypes=[
            ("Image Files", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
            ("All Files", "*.*")
        ]
    )
    
    # If user selected a file (didn't click Cancel)
    if file_path:
        upload_photo_to_json_store(file_path)
    else:
        print("Upload canceled. No file selected.")

if __name__ == "__main__":
    select_and_upload_photo()