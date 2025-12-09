"""
ASGI config for installment_app project.
Handles HTTP connections.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'installment_app.settings')

application = get_asgi_application()
