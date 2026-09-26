from django.shortcuts import render, redirect
from django.contrib import messages

from inventory import models

def home(request):
    return render(request, 'home/index.html')

def intelligence(request):
    return render(request, 'home/intelligence.html')

def precision(request):
    return render(request, 'home/precision.html')

def enterprise(request):
    return render(request, 'home/enterprise.html')


def login(request):
    return render(request, 'login/login.html')


def check_login(request):
    username1 = request.POST["username"]
    password1 = request.POST["password"]
    
    # Use Login table
    try:
        user = models.Login.objects.get(user_name=username1, password=password1)
        
        # Store session data
        request.session['semail'] = user.user_name
        request.session['name'] = user.user_name
        request.session['user_id'] = user.user_id
        request.session['usertype'] = user.user_type
        request.session['role'] = user.user_type.upper()  # Convert to uppercase for consistency
        
        # Redirect based on user_type
        if user.user_type.lower() == 'admin':
            return redirect("../admin_dashboard/admin/")
        elif user.user_type.lower() == 'manager':
            return redirect("../manager_dashboard/dashboard/")
        elif user.user_type.lower() == 'staff':
            return redirect("../staffpanel/dashboard/")
        else:
            messages.error(request, 'Invalid user type')
            return redirect("login")
            
    except models.Login.DoesNotExist:
        messages.error(request, 'Invalid username or password')
        return redirect("login")

def forgot_password(request):
    return render(request, 'login/forgot_password.html')
