import logging
import traceback

try:
    import http.client as httplib
except ImportError:
    import httplib

from django.http import HttpRequest
from django.http import JsonResponse
from functools import wraps



logger = logging.getLogger(__name__)

__all__ = ['handle_uncaught_exception']

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
                                                                        




