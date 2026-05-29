from django.conf import settings


def gemini_key(request):
    return {'gemini_api_key': settings.GEMINI_API_KEY}
