"""
Custom Exception Handler
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that formats error responses consistently.
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        # Customize the response format
        custom_response = {
            'success': False,
            'message': 'An error occurred.',
            'errors': None
        }
        
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                custom_response['message'] = str(response.data['detail'])
            else:
                custom_response['message'] = 'Validation error.'
                custom_response['errors'] = response.data
        elif isinstance(response.data, list):
            custom_response['message'] = response.data[0] if response.data else 'An error occurred.'
        else:
            custom_response['message'] = str(response.data)
        
        response.data = custom_response
    
    return response
