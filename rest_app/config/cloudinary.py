"""
Cloudinary configuration module
"""
import os
from django.conf import settings
import cloudinary
import cloudinary.uploader
import cloudinary.api

def initialize_cloudinary():
    """
    Initialize Cloudinary with credentials from settings or environment variables
    """
    # Try to get credentials from settings.py first
    cloud_name = getattr(settings, 'CLOUDINARY_CLOUD_NAME', None)
    api_key = getattr(settings, 'CLOUDINARY_API_KEY', None)
    api_secret = getattr(settings, 'CLOUDINARY_API_SECRET', None)
    
    # If not in settings, try environment variables
    if not all([cloud_name, api_key, api_secret]):
        cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME')
        api_key = os.environ.get('CLOUDINARY_API_KEY')
        api_secret = os.environ.get('CLOUDINARY_API_SECRET')
    
    # Configure Cloudinary
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )
    
    # Verify configuration
    try:
        # Test the configuration with a simple API call
        cloudinary.api.ping()
        print("Cloudinary configuration successful")
        return True
    except Exception as e:
        print(f"Cloudinary configuration failed: {str(e)}")
        return False

def upload_file(file, folder="uploads", **options):
    """
    Upload a file to Cloudinary
    
    Args:
        file: File object to upload
        folder: Destination folder in Cloudinary
        options: Additional upload options
        
    Returns:
        Dictionary with upload results
    """
    default_options = {
        'folder': folder,
        'resource_type': "auto",
        'overwrite': True
    }
    
    # Merge default options with provided options
    upload_options = {**default_options, **options}
    
    # Upload the file
    try:
        result = cloudinary.uploader.upload(file, **upload_options)
        return {
            'success': True,
            'url': result['secure_url'],
            'public_id': result['public_id'],
            'resource_type': result['resource_type']
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        } 