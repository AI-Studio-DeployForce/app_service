import numpy as np
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
import os
from rest_app.config.cloudinary import upload_file
import tempfile
from datetime import datetime

# --------------------------------------------------------------------------- #
# CONSTANTS                                                                   #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# 1.  Cost constants (USD per pixel) – tune as needed                         #
# --------------------------------------------------------------------------- #
COST_PER_PIXEL = {
    "no_damage":      0,     # inspection only
    "minor_damage":   0.12,  # ~ $120 / m² if 1 px ≈ 0.22 m²
    "major_damage":   0.35,  # ~ $350 / m²
    "destroyed":      0.75,  # ~ $750 / m²
}
SEVERITY_ORDER = ["no_damage", "minor_damage", "major_damage", "destroyed"]
# --------------------------------------------------------------------------- #

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

def _image_breakdown(detail_row):
    """Return per‑image breakdown list for the PDF."""
    area_tot = sum(detail_row[f"area_{c}"] for c in SEVERITY_ORDER) or 1  # avoid ÷0
    out = []
    for cat in SEVERITY_ORDER:
        area   = detail_row[f"area_{cat}"]
        count  = detail_row[f"num_{cat}"]
        pct    = 100 * area / area_tot
        totcost = area * COST_PER_PIXEL[cat]
        out.append({
            "category": cat,
            "count":    count,
            "area":     area,
            "percentage": pct,
            "total_cost": totcost,
        })
    return out


def generate_pdf_report(header_id,
                        detail_entries,
                        summary_stats,
                        grand_area,
                        grand_cost,
                        total_clusters):
    """
    Renders the report HTML to PDF, uploads it to Cloudinary, and
    returns (secure_url, None)  – or (None, error_msg) on failure.
    """
    # ---------------------------------------------------------------
    # Build per‑image section data
    # ---------------------------------------------------------------
    damage_keys = [
        ("no_damage",     "No Damage"),
        ("minor_damage",  "Minor Damage"),
        ("major_damage",  "Major Damage"),
        ("destroyed",     "Destroyed"),
    ]

    image_data = []

    for d in detail_entries:
        # 1) reconstruct the breakdown list -----------------------------------
        brk = []
        for key, label in damage_keys:
            count = d.get(f"num_{key}",   0)
            area  = d.get(f"area_{key}",  0)
            cost  = d.get(f"cost_{key}",  0)

            # keep rows that have at least one non‑zero value
            if any((count, area, cost)):
                brk.append({
                    "category":   label,
                    "count":      count,
                    "area":       area,
                    "total_cost": cost,
                })

        # 2) per‑image totals --------------------------------------------------
        tot_count = sum(b["count"]      for b in brk)
        tot_area  = sum(b["area"]       for b in brk)
        tot_cost  = sum(b["total_cost"] for b in brk)

        # 3) add % share (safe for zero‑area images) ---------------------------
        for b in brk:
            b["percentage"] = (b["area"] / tot_area * 100) if tot_area else 0

        # 4) assemble the structure used by the template ----------------------
        image_data.append({
            "post_image_url": d["post_image_url"],
            "mask_image_url": d["damage_mask_url"],
            "breakdown":      brk,
            "totals": {
                "count": tot_count,
                "area":  tot_area,
                "cost":  tot_cost,
            },
        })

    unit_costs = [
        {"category": "No Damage",    "unit_cost": COST_PER_PIXEL["no_damage"]},
        {"category": "Minor Damage", "unit_cost": COST_PER_PIXEL["minor_damage"]},
        {"category": "Major Damage", "unit_cost": COST_PER_PIXEL["major_damage"]},
        {"category": "Destroyed",    "unit_cost": COST_PER_PIXEL["destroyed"]},
    ]
    # ---------------------------------------------------------------
    # Render HTML with Jinja2 template
    # ---------------------------------------------------------------
    context = {
        "summary_stats":   summary_stats,
        "grand_area":      grand_area,
        "grand_cost":      grand_cost,
        "total_clusters":  total_clusters,
        "image_data":      image_data,
        "generation_date": datetime.utcnow().strftime("%Y‑%m‑%d %H:%M:%S"),
        "unit_costs":       unit_costs,
    }

    template = get_template("report.html")        # Django’s loader
    html     = template.render(context)

    # ---------------------------------------------------------------
    # Create a temporary PDF
    # ---------------------------------------------------------------
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pisa_status = pisa.CreatePDF(html, dest=tmp)
        pdf_path = tmp.name

    if pisa_status.err:
        return None, "Failed to generate PDF"

    # ---------------------------------------------------------------
    # Upload to Cloudinary
    # ---------------------------------------------------------------
    upload_res = upload_file(pdf_path,
                             folder="reports",
                             public_id=f"{header_id}_report")
    os.remove(pdf_path)

    if upload_res["success"]:
        return upload_res["secure_url"], None
    return None, upload_res["error"]

def build_summary(detail_rows):
    """Return summary_stats list + grand totals for the PDF."""
    by_cat = {cat: {"count": 0, "area": 0, "unit_cost": COST_PER_PIXEL[cat]}   # UNIT_COST = same dict you use in Flask
              for cat in SEVERITY_ORDER}

    for row in detail_rows:
        for cat in SEVERITY_ORDER:
            by_cat[cat]["count"] += row[f"num_{cat}"]
            by_cat[cat]["area"]  += row[f"area_{cat}"]

    grand_area = sum(v["area"] for v in by_cat.values())
    grand_cost = 0
    summary    = []
    for cat in SEVERITY_ORDER:
        v = by_cat[cat]
        v["percentage"]  = 0 if grand_area == 0 else 100 * v["area"] / grand_area
        v["total_cost"]  = v["area"] * v["unit_cost"]
        grand_cost      += v["total_cost"]
        summary.append({"category": cat, **v})

    total_clusters = sum(v["count"] for v in by_cat.values())
    return summary, grand_area, grand_cost, total_clusters


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response

def split_filename_and_extension(filename: str) -> tuple[str, str]:
    """
    Split a filename into its base name and extension.

    Args:
        filename (str): The full filename (e.g., 'image_01.png').

    Returns:
        tuple[str, str]: A tuple containing (base_name, extension), e.g.,
                         ('image_01', '.png')
    """
    return os.path.splitext(filename)