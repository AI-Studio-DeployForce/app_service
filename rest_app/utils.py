import numpy as np
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa

def transform_five_reference_coords(image_size, geo_transform):
    """
    Converts selected pixel coordinates (corners and center) to geographical coordinates.

    Parameters:
    - image_size (tuple): (width, height) of the image
    - geo_transform (dict): Geotransform metadata for an image

    Returns:
    - dict: A dictionary with keys for each reference point and values as (lat, lon) tuples.
    """
    width, height = image_size
    geo_params = geo_transform[list(geo_transform.keys())[0]][0]

    lon_top_left, pixel_width, rotation_x, lat_top_left, rotation_y, pixel_height = geo_params

    def pixel_to_geo(x, y):
        lon = lon_top_left + x * pixel_width + y * rotation_x
        lat = lat_top_left + x * rotation_y + y * pixel_height
        return [lat, lon]

    reference_coords = {
        "top_left": pixel_to_geo(0, 0),
        "top_right": pixel_to_geo(width - 1, 0),
        "center": pixel_to_geo(width // 2, height // 2),
        "bottom_left": pixel_to_geo(0, height - 1),
        "bottom_right": pixel_to_geo(width - 1, height - 1)
    }

    return reference_coords

def validate_uploaded_images(image_files):
    """
    Validate that each pre-disaster image has a corresponding post-disaster image.

    Args:
        image_files (list): List of uploaded InMemoryUploadedFile objects.

    Returns:
        (bool, list): Tuple of validation status and a list of base names (without _pre/_post suffixes).
    """
    pre_files = set()
    post_files = set()
    base_names = []

    for image in image_files:
        filename = image.name
        if "_pre_disaster" in filename:
            base_name = filename.replace("_pre_disaster", "").replace(".png", "")
            pre_files.add(base_name)
        elif "_post_disaster" in filename:
            base_name = filename.replace("_post_disaster", "").replace(".png", "")
            post_files.add(base_name)

    matched = pre_files == post_files
    base_names = list(pre_files & post_files)

    return matched, base_names


def validate_json_structure(json_data, expected_image_names):
    """
    Validate the geotransform JSON file structure.

    Args:
        json_data (dict): Loaded JSON content.
        expected_image_names (list): Expected image file names from uploaded images (with _pre and _post suffixes).

    Returns:
        bool: Whether the structure is valid.
    """
    if not isinstance(json_data, dict):
        return False

    required_count = len(expected_image_names) * 2  # pre and post for each

    if len(json_data.keys()) != required_count:
        return False

    # Collect expected image keys
    expected_keys = set()
    for base_name in expected_image_names:
        expected_keys.add(f"{base_name}_pre_disaster.png")
        expected_keys.add(f"{base_name}_post_disaster.png")

    for key, value in json_data.items():
        if key not in expected_keys:
            return False
        if not isinstance(value, list) or len(value) != 2:
            return False
        if not isinstance(value[0], list) or len(value[0]) != 6:
            return False
        if not isinstance(value[1], str):
            return False

    return True

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response