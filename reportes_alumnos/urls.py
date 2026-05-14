"""
URL configuration for reportes_alumnos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from generar_reporte import views

urlpatterns = [
    path("reporte/", views.index, name="inicio"),
    path("reporte/login", views.login_google, name="login_google"),
    path("reporte/generar", views.generar_callback, name="generar_callback"),
    path("reporte/descargar/", views.generar_reporte),
]