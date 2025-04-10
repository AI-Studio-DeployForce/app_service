from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import datetime
import json
import cloudinary.uploader
from rest_app.config.cloudinary import upload_file
from django.conf import settings
import requests
from rest_app.utils import transform_five_reference_coords, render_to_pdf, validate_json_structure, validate_uploaded_images
from rest_app.config.supabase import insert_row, insert_multiple_rows

IMAGE_SIZE = (512, 512)  # Width x Height of the mask or satellite image

def home(request):
    return render(request, 'home.html')

def upload(request):
    return render(request, 'upload.html')

def inference(request):
    if request.method == 'POST':
        image_files = request.FILES.getlist('image_files')
        json_file = request.FILES.get('json_file')

        # Validate image pairs
        valid_images, base_names = validate_uploaded_images(image_files)
        if not valid_images:
            return JsonResponse({'status': 'error', 'message': 'Image pairs (pre/post) are incomplete or mismatched.'}, status=400)

        # Validate JSON structure
        try:
            json_data = json.load(json_file)
            if not validate_json_structure(json_data, base_names):
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON structure or image name mismatch.'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)

        # Upload images to Cloudinary
        cloudinary_urls = {}
        for image in image_files:
            result = upload_file(image)
            cloudinary_urls[image.name] = result['secure_url']

        # # TODO: call the inference API, the code below is just a temporary dummy data
        # payload = {
        #     'images': list(cloudinary_urls.values()),
        # }
        # response = {
        #     "mask_image_urls": ["https://resizing.flixster.com/TNUObVesnGUFtTYveu0dAVb2tlg=/fit-in/352x330/v2/https://resizing.flixster.com/-XZAfHZM39UwaGJIFWKAE8fS0ak=/v3/t/assets/720474_v9_bc.jpg"],
        #     "damage_severities": [{
        #         "num_no_damage": 5,
        #         "num_minor_damage": 10,
        #         "num_major_damage": 3,
        #         "num_destroyed": 2,
        #     }],
        #     "image_urls": [{"pre_disaster": "", "post_disaster": ""}],
        # }
        # # NOTE: image_urls are used to align the prediction results with particular image pair

        # try:
        #     response = requests.post(settings.INFERENCE_API_URL, json=payload)
        #     if response.status_code != 200:
        #         return JsonResponse({'status': 'error', 'message': 'Inference API failed'}, status=500)

        #     inference_data = response.json()
        #     mask_urls = inference_data.get("mask_image_urls", [])
        #     damage_stats = inference_data.get("damage_severities", [])
        #     image_mappings = inference_data.get("image_urls", [])

        # except Exception as e:
        #     return JsonResponse({'status': 'error', 'message': f"Inference API error: {e}"}, status=500)
        
        # Dummy inference results
        mask_url = "https://resizing.flixster.com/TNUObVesnGUFtTYveu0dAVb2tlg=/fit-in/352x330/v2/https://resizing.flixster.com/-XZAfHZM39UwaGJIFWKAE8fS0ak=/v3/t/assets/720474_v9_bc.jpg"

        # TODO: process report here, after that upload that report to cloudinary and get the URL
        report_url = "https://www.nrma.com.au/content/dam/insurance-brands-aus/nrma/au/en/documents/car/nrma-car-pds-nrmamotpds-rev2-0923.pdf"
        
        image_size = IMAGE_SIZE

        # Insert header
        execution_header = {
            "upload_time": datetime.utcnow().isoformat(),
            "report_url": report_url,
        }
        header_inserted = insert_row("execution_headers", execution_header)
        header_id = header_inserted[0].get("id") if header_inserted else None

        # Insert details with geo_params
        detail_entries = []
        for base in base_names:
            pre_img = [k for k in cloudinary_urls if f"{base}_pre_disaster" in k][0]
            post_img = [k for k in cloudinary_urls if f"{base}_post_disaster" in k][0]

            # Get geo_params by pre_img name
            geo_key = pre_img
            geo_params = json_data.get(geo_key, [])[0] if isinstance(json_data.get(geo_key), list) else None

            detail_entries.append({
                "header_id": header_id,
                "pre_image_name": pre_img,
                "pre_image_url": cloudinary_urls[pre_img],
                "post_image_name": post_img,
                "post_image_url": cloudinary_urls[post_img],
                "mask_image_name": "simulated_mask.png",
                "mask_image_url": mask_url,
                "num_no_damage": 5,
                "num_minor_damage": 10,
                "num_major_damage": 3,
                "num_destroyed": 2,
                "geo_params": geo_params
            })

        insert_multiple_rows("execution_details", detail_entries)

        # If single image pair → navigate to inference page
        if len(base_names) == 1:
            # Get reference coords
            geo_transform = {
                list(json_data.keys())[0]: json_data[list(json_data.keys())[0]]
            }
            reference_coords = transform_five_reference_coords(image_size, geo_transform)

            return render(request, 'inference.html', {
                'image_urls': [cloudinary_urls[pre_img], cloudinary_urls[post_img]],
                'mask_urls': [mask_url],
                'report_url': report_url,
                'reference_coords': reference_coords
            })

        # Multiple pairs → show report
        return render(request, 'upload.html', {
            'success': True,
            'report_url': report_url
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


# def inference(request):
#     if request.method == 'POST':
#         coordinates = {"lat": 14.414359, "lon": -90.823070}

#         # Simulate image size and geo-transform metadata
#         image_size = (1024, 1024)  # Width x Height of the mask or satellite image
#         geo_transform = {
#             "guatemala-volcano_00000020_pre_disaster.png": [
#                 [-90.82307020932015, 4.488628277641187e-06, 0.0,
#                  14.414359902299086, 0.0, -4.488628277641187e-06],
#                 "GEOGCS[\"WGS 84\",DATUM[\"WGS_1984\",SPHEROID[\"WGS 84\",6378137,...]"
#             ]
#         }

#         # Call util function to get 5 coordinates
#         reference_coords = transform_five_reference_coords(image_size, geo_transform)

#         return render(request, 'inference.html', {
#             'image_urls': [
#                 "https://hips.hearstapps.com/hmg-prod/images/niallhoran-shot1-358-6478b67555832.jpg",
#                 "https://d27o7y1r7mnbwc.cloudfront.net/media/uploads/clients/leo-woodall/images/gallery/2023-10-26_105555_LeoWoodallHeadshot2.jpg"
#             ],
#             'mask_urls': [
#                 "https://resizing.flixster.com/TNUObVesnGUFtTYveu0dAVb2tlg=/fit-in/352x330/v2/https://resizing.flixster.com/-XZAfHZM39UwaGJIFWKAE8fS0ak=/v3/t/assets/720474_v9_bc.jpg"
#             ],
#             'report_url': "https://www.nrma.com.au/content/dam/insurance-brands-aus/nrma/au/en/documents/car/nrma-car-pds-nrmamotpds-rev2-0923.pdf",
#             'reference_coords': reference_coords  # This is what the frontend will use for interpolation,
#         })

#         # Handle the uploaded files
#         image_files = request.FILES.getlist('image_files')
#         json_file = request.FILES.get('json_file')

#         # Validate image pairs
#         valid_images, base_names = validate_uploaded_images(image_files)
#         if not valid_images:
#             return JsonResponse({'status': 'error', 'message': 'Image pairs (pre/post) are incomplete or mismatched.'}, status=400)

#         # Validate JSON structure
#         try:
#             json_data = json.load(json_file)
#             if not validate_json_structure(json_data, base_names):
#                 return JsonResponse({'status': 'error', 'message': 'Invalid JSON structure or image name mismatch.'}, status=400)
#         except json.JSONDecodeError:
#             return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)

#         # Validate JSON file
#         try:
#             json_data = json.load(json_file)
#             if not validate_json_structure(json_data):
#                 return JsonResponse({'status': 'error', 'message': 'Invalid JSON structure'}, status=400)
#         except json.JSONDecodeError:
#             return JsonResponse({'status': 'error', 'message': 'Invalid JSON file'}, status=400)

#         # Upload images to Cloudinary
#         image_urls = []
#         for image in image_files:
#             upload_result = cloudinary.uploader.upload(image)
#             image_urls.append(upload_result['secure_url'])

#         # Prepare data for the API request
#         api_payload = {
#             'images': image_urls,
#             'json_data': json_data
#         }

#         # Send a REST API request to the microservice
#         try:
#             response = requests.post(settings.INFERENCE_API_URL, json=api_payload)
#             response_data = response.json()

#             # Check for successful response
#             if response.status_code == 200:
#                 # Assuming the response contains mask URLs and report URL
#                 mask_urls = response_data.get('mask_urls', [])
#                 report_url = response_data.get('report_url', '')

#                 # Redirect to the inference page with the results
#                 return render(request, 'inference.html', {
#                     'image_urls': image_urls,
#                     'mask_urls': mask_urls,
#                     'report_url': report_url
#                 })
#             else:
#                 return JsonResponse({'status': 'error', 'message': 'Error from inference service'}, status=500)

#         except Exception as e:
#             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

#     return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400) 

def generate_pdf_report(request):
    context = {
        'title': 'Damage Report',
        'buildings': [
            {'id': 1, 'severity': 'Destroyed', 'lat': 12.34, 'lon': 56.78},
            {'id': 2, 'severity': 'Major', 'lat': 12.35, 'lon': 56.79},
        ]
    }
    return render_to_pdf('report.html', context)