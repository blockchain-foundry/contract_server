from django.http import JsonResponse
from rest_framework.views import status


def data_response(data):
    response = {
        "data": data
    }
    return JsonResponse(response, status=status.HTTP_200_OK)


def error_response(http_code, message="", error_code=""):
    if error_code == "":
        error_code = http_code
    response = {
        "errors": [
            {
                "code": error_code,
                "message": message,
            }
        ]
    }
    return JsonResponse(response, status=http_code)
