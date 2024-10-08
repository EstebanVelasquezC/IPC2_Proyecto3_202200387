# archivo urls.py
from django.urls import path
from app import views

urlpatterns = [
    path('', views.index),
    path('about', views.about)
]
