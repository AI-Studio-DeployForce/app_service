import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.conf import settings
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Cloudinary
def initialize_cloudinary():
    """
    Initialize Cloudinary with credentials from environment variables.
    This function should be called once when the app starts.
    """
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True
    )
    return cloudinary

# Initialize the client
cloudinary_client = initialize_cloudinary()
CLOUDINARY_FOLDER_NAME = os.getenv('CLOUDINARY_FOLDER_NAME', 'default_folder')

# File management functions
def upload_file(file, folder=None, public_id=None):
    """
    Upload a file to Cloudinary
    
    Args:
        file: The file to upload
        folder: Optional folder name to organize files
        public_id: Optional custom public ID for the file
        
    Returns:
        Dictionary with upload result information
    """
    upload_options = {
        'resource_type': 'auto',  # Automatically detect resource type
    }
    
    upload_options['folder'] = CLOUDINARY_FOLDER_NAME
    if folder:
        upload_options['folder'] += ("/" + folder)
    
    if public_id:
        upload_options['public_id'] = public_id
    
    try:
        result = cloudinary.uploader.upload(file, **upload_options)
        return {
            'success': True,
            'secure_url': result['secure_url'],
            'public_id': result['public_id'],
            'resource_type': result['resource_type'],
            'format': result.get('format', ''),
            'created_at': result['created_at']
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def delete_file(public_id, resource_type='image'):
    """
    Delete a file from Cloudinary
    
    Args:
        public_id: The public ID of the file to delete
        resource_type: The resource type (image, video, raw)
        
    Returns:
        Dictionary with deletion result
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return {
            'success': True,
            'result': result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }