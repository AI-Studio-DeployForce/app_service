from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import datetime
import json
from rest_app.config.cloudinary import upload_file
from django.conf import settings
import requests
from rest_app.utils import transform_five_reference_coords, render_to_pdf, validate_json_structure, validate_uploaded_images, split_filename_and_extension, generate_pdf_report, build_summary
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
        json_file   = request.FILES.get('json_file')

        # ------------------------------------------------------------------ #
        # 1)  validate uploads (unchanged)                                   #
        # ------------------------------------------------------------------ #
        valid_images, base_names = validate_uploaded_images(image_files)
        if not valid_images:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Image pairs (pre/post) are incomplete or mismatched.'},
                status=400
            )

        try:
            json_data = json.load(json_file)
            if not validate_json_structure(json_data, base_names):
                return JsonResponse(
                    {'status': 'error',
                     'message': 'Invalid JSON structure or image name mismatch.'},
                    status=400
                )
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error',
                                 'message': 'Invalid JSON format.'},
                                status=400)

        # ------------------------------------------------------------------ #
        # 2)  upload originals to Cloudinary (unchanged)                     #
        # ------------------------------------------------------------------ #
        cloudinary_payload, cloudinary_mapping = [], {}
        image_map = {img.name: img for img in image_files}

        for base in base_names:
            pre_name  = f"{base}_pre_disaster.png"
            post_name = f"{base}_post_disaster.png"
            upload_pair = {}

            for img_name in (pre_name, post_name):
                if img_name not in image_map:
                    return JsonResponse(
                        {'status': 'error',
                         'message': f'Missing file: {img_name}'}, status=400)
                res = upload_file(image_map[img_name],
                                  folder='inputs',
                                  public_id=img_name)
                if not res['success']:
                    return JsonResponse(
                        {'status': 'error',
                         'message': f'Failed to upload {img_name}: {res["error"]}'},
                        status=500)
                upload_pair[img_name]       = res['secure_url']
                cloudinary_mapping[img_name] = res['secure_url']

            cloudinary_payload.append(upload_pair)

        # ------------------------------------------------------------------ #
        # 3)  call the Flask inference API (unchanged)                       #
        # ------------------------------------------------------------------ #
        try:
            flask_url = os.getenv('INFERENCE_API_URL',
                                  'http://127.0.0.1:8001/predict')
            flask_resp = requests.post(flask_url,
                                       json={'images': cloudinary_payload},
                                       timeout=9999)
            if flask_resp.status_code != 200:
                return JsonResponse({'status': 'error',
                                     'message': 'Flask prediction failed'},
                                    status=500)
            flask_data = flask_resp.json()
        except Exception as exc:
            return JsonResponse({'status': 'error',
                                 'message': f'Flask call failed: {exc}'},
                                status=500)

        # ------------------------------------------------------------------ #
        # 4)  persist results in Supabase                                    #
        # ------------------------------------------------------------------ #
        header_id = insert_row('execution_headers',
                               {'upload_time': datetime.utcnow().isoformat()}
                               )[0]['id']

        detail_entries = []
        for idx, base in enumerate(base_names):
            pre_img  = next(k for k in cloudinary_mapping
                            if k.startswith(f'{base}_pre_disaster'))
            post_img = next(k for k in cloudinary_mapping
                            if k.startswith(f'{base}_post_disaster'))

            pre_mask_url  = flask_data['mask_image_urls'][idx][pre_img]
            post_mask_url = flask_data['mask_image_urls'][idx][post_img]
            damage        = flask_data['damage_severities'][idx]

            # ---- area / cost summaries ----------------------------------- #
            area_br  = damage.get('area_breakdown',  {})
            cost_br  = damage.get('cost_breakdown',  {})
            total_cost = sum(cost_br.values())

            def safe_get(d, key):
                # ensures 0 if class absent (e.g. no clusters of that type)
                return float(d.get(key, 0))

            # ---- geo‑transform params ------------------------------------ #
            geo_key    = pre_img          # key inside the uploaded json
            geo_params = (json_data.get(geo_key, []) or [None])[0]

            detail_entries.append({
                'header_id': header_id,

                'pre_image_name':  pre_img,
                'pre_image_url':   cloudinary_mapping[pre_img],
                'post_image_name': post_img,
                'post_image_url':  cloudinary_mapping[post_img],

                'localisation_mask_name':
                    f"{split_filename_and_extension(pre_img)[0]}_mask"
                    f"{split_filename_and_extension(pre_img)[1]}",
                'localisation_mask_url': pre_mask_url,

                'damage_mask_name':
                    f"{split_filename_and_extension(post_img)[0]}_mask"
                    f"{split_filename_and_extension(post_img)[1]}",
                'damage_mask_url': post_mask_url,

                # --- counts ------------------------------------------------
                'num_no_damage':   damage.get('num_no_damage',   0),
                'num_minor_damage':damage.get('num_minor_damage',0),
                'num_major_damage':damage.get('num_major_damage',0),
                'num_destroyed':   damage.get('num_destroyed',   0),

                # --- NEW area columns (pixels) -----------------------------
                'area_no_damage':   safe_get(area_br, 'no_damage'),
                'area_minor_damage':safe_get(area_br, 'minor_damage'),
                'area_major_damage':safe_get(area_br, 'major_damage'),
                'area_destroyed':   safe_get(area_br, 'destroyed'),

                # --- NEW cost columns (USD) --------------------------------
                'cost_no_damage':   safe_get(cost_br, 'no_damage'),
                'cost_minor_damage':safe_get(cost_br, 'minor_damage'),
                'cost_major_damage':safe_get(cost_br, 'major_damage'),
                'cost_destroyed':   safe_get(cost_br, 'destroyed'),

                'geo_params': geo_params,
            })

        # bulk‑insert all detail rows
        insert_multiple_rows('execution_details', detail_entries)

        # ------------------------------------------------------------------ #
        # 5)  generate the PDF report & render response (unchanged)          #
        # ------------------------------------------------------------------ #
        summary_stats, grand_area, grand_cost, total_clusters = build_summary(detail_entries)
        report_url, err = generate_pdf_report(
                header_id,
                detail_entries,
                summary_stats=summary_stats,
                grand_area=grand_area,
                grand_cost=grand_cost,
                total_clusters=total_clusters,
        )
        if not report_url:
            return JsonResponse({'status':'error','message':err}, status=500)

        if len(base_names) == 1:
            image_size = IMAGE_SIZE
            reference_coords = transform_five_reference_coords(
                image_size,
                {f"{base_names[0]}_pre_disaster.png":
                    json_data.get(f"{base_names[0]}_pre_disaster.png")}
            )
            return render(request, 'inference.html', {
                'image_urls': {
                    'pre':  cloudinary_mapping[pre_img],
                    'post': cloudinary_mapping[post_img]
                },
                'mask_urls': {
                    'localisation_mask': pre_mask_url,
                    'damage_severity_mask': post_mask_url
                },
                'total_estimated_cost': total_cost,
                'cost_breakdown': cost_br,
                'report_url': report_url,
                'reference_coords': reference_coords,
                "damage": damage
            })

        return render(request, 'upload.html',
                      {'success': True, 'report_url': report_url})

    # ---------------------------------------------------------------------- #
    return JsonResponse({'status': 'error', 'message': 'Invalid request'},status=400)