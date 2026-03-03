import oci
from app.core.config import settings
import uuid

import os

def get_object_storage_client():
    if not os.path.exists(settings.oci_config_file):
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Cloud Storage is not configured. Please upload credentials via /api/v1/config/oci (Step 2)")
        
    config = oci.config.from_file(file_location=settings.oci_config_file, profile_name=settings.oci_config_profile)
    return oci.object_storage.ObjectStorageClient(config), config["tenancy"]

def upload_document(file_content: bytes, filename: str) -> str:
    client, tenancy = get_object_storage_client()
    namespace = client.get_namespace(compartment_id=tenancy).data
    
    unique_filename = f"{uuid.uuid4()}_{filename}"
    
    # Upload to Oracle Object Storage
    client.put_object(
        namespace,
        settings.oci_bucket_name,
        unique_filename,
        file_content
    )
    return unique_filename

def download_document(object_name: str) -> bytes:
    client, tenancy = get_object_storage_client()
    namespace = client.get_namespace(compartment_id=tenancy).data
    response = client.get_object(namespace, settings.oci_bucket_name, object_name)
    return response.data.content

def delete_document(object_name: str):
    client, tenancy = get_object_storage_client()
    namespace = client.get_namespace(compartment_id=tenancy).data
    try:
        client.delete_object(namespace, settings.oci_bucket_name, object_name)
    except oci.exceptions.ServiceError as e:
        if e.status == 404:
            pass # Object is already missing, safely ignore
        else:
            raise e
