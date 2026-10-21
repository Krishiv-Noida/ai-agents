"""
ASGI config for core_project.

Configured for asynchronous execution and streaming responses with Django & LangGraph.
It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/stable/howto/deployment/asgi/
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_project.settings")

application = get_asgi_application()
