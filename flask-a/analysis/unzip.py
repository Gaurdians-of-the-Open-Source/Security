# analysis/unzip.py
import os
import zipfile
import uuid

UPLOAD_DIR = "uploads"

def save_and_unzip(file_storage):
    # Unique job ID and path
    job_id = str(uuid.uuid4())
    job_path = os.path.join(UPLOAD_DIR, job_id)
    zip_path = os.path.join(job_path, "uploaded.zip")

    os.makedirs(job_path, exist_ok=True)

    # zip file save
    file_storage.save(zip_path)

    # unzip
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(job_path)

    return job_path
