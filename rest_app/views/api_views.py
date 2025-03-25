from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from rest_app.models import *
from rest_app.core.utils import get_client_ip

@csrf_exempt
def api_example(request):
    """
    Example API endpoint that handles GET and POST requests
    """
    if request.method == 'GET':
        # Access settings from settings.py
        max_items = getattr(settings, 'MAX_ITEMS_PER_PAGE', 10)
        
        # Example response
        data = {
            'status': 'success',
            'message': 'API is working',
            'max_items': max_items,
            'client_ip': get_client_ip(request)
        }
        return JsonResponse(data)
        
    elif request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            
            # Process the data
            # Example: Create a new record
            # new_item = YourModel.objects.create(**data)
            
            # Return success response
            return JsonResponse({
                'status': 'success',
                'message': 'Data received successfully',
                'received_data': data
            })
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    # Method not allowed
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405) 