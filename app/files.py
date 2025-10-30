from fastapi import APIRouter, UploadFile, File, HTTPException
from google.cloud import storage
import uuid

router = APIRouter(prefix="/files", tags=["files"])

@router.post("/upload")
def upload_file(file: UploadFile = File(...)):
    client = storage.Client()
    bucket = client.bucket("sistemab-montaj.appspot.com")
    filename = f"docs/{uuid.uuid4()}_{file.filename}"
    blob = bucket.blob(filename)
    blob.upload_from_file(file.file, content_type=file.content_type)
    url = blob.public_url
    return {"url": url, "name": file.filename}
