from django.urls import path
from app import views

urlpatterns = [
    path('', views.index, name='index'),
    path('ayuda', views.ayuda, name='ayuda'),
    path('peticiones', views.peticiones, name='peticiones'),
    path('reset/', views.reset_api_view, name='reset_api'),
    path('consultarDatos/', views.consultar_datos, name='consultar_datos'),
]
