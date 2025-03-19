import numpy as np

def transform_pixel_to_geo(image_size, geo_transform):
    """
    Converts pixel coordinates to geographical coordinates (latitude, longitude).

    Parameters:
    - image_size (tuple): (width, height) of the image.
    - geo_transform (dict): Geotransform metadata for an image.
    
    Returns:
    - geo_matrix (numpy.ndarray): 2D matrix containing (latitude, longitude) for each pixel.
    - center_point (tuple): (latitude, longitude) of the image center.
    """
    width, height = image_size
    geo_params = geo_transform[list(geo_transform.keys())[0]][0]  # Extract the first geo-transform list
    
    lon_top_left, pixel_width, rotation_x, lat_top_left, rotation_y, pixel_height = geo_params
    
    # Create an empty matrix to store latitude, longitude for each pixel
    geo_matrix = np.empty((height, width), dtype=object)

    for y in range(height):
        for x in range(width):
            lon = lon_top_left + x * pixel_width + y * rotation_x
            lat = lat_top_left + x * rotation_y + y * pixel_height
            geo_matrix[y, x] = (lat, lon)
    
    # Compute the center point of the image
    center_x = width // 2
    center_y = height // 2
    center_point = geo_matrix[center_y, center_x]

    return geo_matrix, center_point