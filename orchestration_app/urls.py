"""
Endpoint routing for the orchestration_app.
"""
from django.urls import path
from orchestration_app.views import orchestrate_chat

urlpatterns = [
    # Multi-agent streaming orchestration endpoint
    # Accessible via /api/orchestrate/
    path("orchestrate/", orchestrate_chat, name="orchestrate_chat"),
]
