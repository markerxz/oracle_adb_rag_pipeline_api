import oci
from app.core.config import settings
import uuid

def get_object_storage_client():
    # Uses the default local ~/.oci/config profile for Auth
    config = oci.config.from_file(profile_name=settings.oci_config_profile)
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

def delete_document(object_name: str):
    client, tenancy = get_object_storage_client()
    namespace = client.get_namespace(compartment_id=tenancy).data
    client.delete_object(namespace, settings.oci_bucket_name, object_name)
