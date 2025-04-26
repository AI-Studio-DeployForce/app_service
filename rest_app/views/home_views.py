from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import datetime
import json
from rest_app.config.cloudinary import upload_file
from django.conf import settings
import requests
from rest_app.utils import transform_five_reference_coords, render_to_pdf, validate_json_structure, validate_uploaded_images, split_filename_and_extension, generate_pdf_report
from rest_app.config.supabase import insert_row, insert_multiple_rows
import os
from dotenv import load_dotenv
load_dotenv()

IMAGE_SIZE = (512, 512)  # Width x Height of the mask or satellite image

def home(request):
    return render(request, 'home.html')

def upload(request):
    return render(request, 'upload.html')

def inference(request):
    if request.method == 'POST':
        image_files = request.FILES.getlist('image_files')
        json_file = request.FILES.get('json_file')

        # Step 1: Validate image pairs
        valid_images, base_names = validate_uploaded_images(image_files)
        if not valid_images:
            return JsonResponse({'status': 'error', 'message': 'Image pairs (pre/post) are incomplete or mismatched.'}, status=400)

        # Step 2: Validate JSON
        try:
            json_data = json.load(json_file)
            if not validate_json_structure(json_data, base_names):
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON structure or image name mismatch.'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)

        # Step 3: Upload to Cloudinary
        cloudinary_payload = []  # [{"pre_name.png": url, "post_name.png": url}, ...]
        image_map = {img.name: img for img in image_files}
        cloudinary_mapping = {}  # flat map for lookup later

        for base in base_names:
            pre_name = f"{base}_pre_disaster.png"
            post_name = f"{base}_post_disaster.png"
            upload_pair = {}

            for img_name in [pre_name, post_name]:
                if img_name not in image_map:
                    return JsonResponse({'status': 'error', 'message': f"Missing file: {img_name}"}, status=400)
                upload_result = upload_file(image_map[img_name], folder="inputs", public_id=img_name)
                if not upload_result['success']:
                    return JsonResponse({'status': 'error', 'message': f"Failed to upload {img_name}: {upload_result['error']}"}, status=500)

                upload_pair[img_name] = upload_result['secure_url']
                cloudinary_mapping[img_name] = upload_result['secure_url']

            cloudinary_payload.append(upload_pair)

        # Step 4: Call Flask Prediction API
        try:
            print(os.getenv('INFERENCE_API_URL', 'http://127.0.0.1:8001/predict'))
            flask_response = requests.post(
                os.getenv('INFERENCE_API_URL', 'http://127.0.0.1:8001/predict'),
                json={'images': cloudinary_payload},
                timeout=50
            )
            if flask_response.status_code != 200:
                return JsonResponse({'status': 'error', 'message': 'Flask prediction failed'}, status=500)
            flask_data = flask_response.json()
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Flask call failed: {str(e)}'}, status=500)

        # Step 5: Save to Supabase
        header_inserted = insert_row("execution_headers", {
            "upload_time": datetime.utcnow().isoformat(),
        })
        header_id = header_inserted[0].get("id") if header_inserted else None

        detail_entries = []
        for idx, base in enumerate(base_names):
            pre_img = [k for k in cloudinary_mapping if f"{base}_pre_disaster" in k][0]
            post_img = [k for k in cloudinary_mapping if f"{base}_post_disaster" in k][0]
            pre_mask_url = flask_data["mask_image_urls"][idx].get(pre_img)
            post_mask_url = flask_data["mask_image_urls"][idx].get(post_img)
            damage = flask_data["damage_severities"][idx]

            geo_key = pre_img
            geo_params = json_data.get(geo_key, [])[0] if isinstance(json_data.get(geo_key), list) else None

            detail_entries.append({
                "header_id": header_id,
                "pre_image_name": pre_img,
                "pre_image_url": cloudinary_mapping[pre_img],
                "post_image_name": post_img,
                "post_image_url": cloudinary_mapping[post_img],
                "localisation_mask_name": f"{split_filename_and_extension(pre_img)[0]}_mask{split_filename_and_extension(pre_img)[1]}",
                "localisation_mask_url": pre_mask_url,
                "damage_mask_name": f"{split_filename_and_extension(post_img)[0]}_mask{split_filename_and_extension(post_img)[1]}",
                "damage_mask_url": post_mask_url,
                "num_no_damage": damage.get("num_no_damage", 0),
                "num_minor_damage": damage.get("num_minor_damage", 0),
                "num_major_damage": damage.get("num_major_damage", 0),
                "num_destroyed": damage.get("num_destroyed", 0),
                "geo_params": geo_params
            })

        insert_multiple_rows("execution_details", detail_entries)

         # Step 6: Report Generation
        report_url, error = generate_pdf_report(header_id, detail_entries)
        if not report_url:
            return JsonResponse({'status': 'error', 'message': error}, status=500)

        # Step 7: Render single inference or upload summary
        if len(base_names) == 1:
            image_size = IMAGE_SIZE
            reference_coords = transform_five_reference_coords(
                image_size,
                {base_names[0] + "_pre_disaster.png": json_data.get(base_names[0] + "_pre_disaster.png")}
            )
            return render(request, 'inference.html', {
                'image_urls': {"pre": cloudinary_mapping[pre_img], "post": cloudinary_mapping[post_img]},
                'mask_urls': {
                    "localisation_mask": flask_data["mask_image_urls"][0][pre_img],
                    "damage_severity_mask": flask_data["mask_image_urls"][0][post_img]
                },
                'report_url': report_url,
                'reference_coords': reference_coords
            })

        return render(request, 'upload.html', {
            'success': True,
            'report_url': report_url
        })

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)