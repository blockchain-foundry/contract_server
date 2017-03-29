import logging
import traceback

try:
    import http.client as httplib
except ImportError:
    import httplib

from django.http import JsonResponse
from django.conf import settings
from functools import wraps

import json

from .error_codes import ERROR_CODE
from .response_utils import error_response

logger = logging.getLogger(__name__)

__all__ = ['handle_uncaught_exception']


def handle_apiversion(view_func):
    """
    This decorator handles api versioning.
    Reject the requests with wrong api-version and append apiVersion fields in response.
    """

    @wraps(view_func)
    def wrapper(self, form):
        API_VERSION = getattr(settings, "API_VERSION", None)
        request_api_version = form.cleaned_data.get('apiVersion')
        if request_api_version and request_api_version != API_VERSION:
            return error_response(httplib.NOT_ACCEPTABLE, "Wrong api version", ERROR_CODE['wrong_api_version'])
        response = view_func(self, form)
        content = json.loads(response.content.decode('utf-8'))
        content['apiVersion'] = API_VERSION
        response.content = response.make_bytes(json.dumps(content))
        return response
    return wrapper


def handle_apiversion_apiview(view_func):
    """
    This decorator handles api versioning.
    Reject the requests with wrong api-version and append apiVersion fields in response.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        API_VERSION = getattr(settings, "API_VERSION", None)

        request_api_version = args[1].POST.get('apiVersion')
        if request_api_version and request_api_version != API_VERSION:
            return error_response(httplib.NOT_ACCEPTABLE, "Wrong api version", ERROR_CODE['wrong_api_version'])
        response = view_func(*args, **kwargs)
        content = json.loads(response.content.decode('utf-8'))
        content['apiVersion'] = API_VERSION
        response.content = response.make_bytes(json.dumps(content))
        return response
    return wrapper


def handle_uncaught_exception(view_func):
    """
    This decorator catches all exception that thrown by the view_func,
    log the exception and return json format error response instead of a html
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            response = {"errors": [{
                "message": 'internal server error',
            }]
            }
            return JsonResponse(response, status=httplib.INTERNAL_SERVER_ERROR)
    return wrapper
