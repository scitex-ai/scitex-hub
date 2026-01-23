"""
Scientific Figure Editor - Image Conversion API Views
REST API endpoints for image format conversion (PNG to TIFF)
"""

import json
import base64
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


@require_http_methods(["POST"])
@csrf_exempt
def convert_png_to_tiff(request):
    """
    Convert PNG image to TIFF format at 300 DPI.

    POST /api/vis/convert/png-to-tiff/

    Request body (JSON):
    {
      "image_data": "data:image/png;base64,...",  // Base64 PNG data
      "filename": "figure.png"  // Optional output filename
    }

    Response:
    - Success: TIFF image file download
    - Error: JSON with error details
    """
    try:
        from PIL import Image
        import io

        data = json.loads(request.body)
        image_data = data.get('image_data')
        filename = data.get('filename', 'figure.tiff')

        if not image_data:
            return JsonResponse({
                'error': 'No image data provided'
            }, status=400)

        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        # Decode base64
        img_bytes = base64.b64decode(image_data)

        # Open with PIL
        img = Image.open(io.BytesIO(img_bytes))

        # Convert RGBA to RGB if necessary (TIFF doesn't always handle alpha well)
        if img.mode == 'RGBA':
            # Create white background
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[3])  # Use alpha channel as mask
            img = rgb_img
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Save as TIFF with 300 DPI
        output = io.BytesIO()
        img.save(output, format='TIFF', dpi=(300, 300), compression='lzw')
        output.seek(0)

        # Return as file download
        response = HttpResponse(output.getvalue(), content_type='image/tiff')
        response['Content-Disposition'] = f'attachment; filename="{filename.replace(".png", ".tiff")}"'
        return response

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Conversion failed: {str(e)}'
        }, status=500)
