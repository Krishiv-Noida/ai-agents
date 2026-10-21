"""
URL configuration for core_project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Route all multi-agent orchestration endpoints to orchestration_app
    path("api/", include("orchestration_app.urls")),
]
