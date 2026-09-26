"""
URL configuration for inventory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path,include
from . import views

urlpatterns = [
   
    path('',views.home,name="home"),
    path('intelligence/', views.intelligence, name='intelligence'),
    path('precision/', views.precision, name='precision'),
    path('enterprise/', views.enterprise, name='enterprise'),
    path('login/', views.login, name='login'),
    path('check-login/', views.check_login, name='check_login'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),

    path('admin_dashboard/',include('admin.urls')),
    path('manager_dashboard/',include('manager.urls')),
    path('staffpanel/',include('staffpanel.urls')),
]
