# users/student_urls.py

from django.urls import path
# Import Django's built-in authentication views
from django.contrib.auth import views as auth_views 
from . import views 

urlpatterns = [
    # Your existing student login path
    path('login/', views.student_login, name='student_login'), 
    
    # --- Password Reset Paths (Required for Forgot Password link) ---
    
    # 1. The initial form (MUST be named 'password_reset')
    path(
        'password_reset/', 
        auth_views.PasswordResetView.as_view(template_name='users/password_reset_form.html'), 
        name='password_reset' 
    ),
    
    # 2. Confirmation that the email was sent
    path(
        'password_reset/done/', 
        auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), 
        name='password_reset_done'
    ),
    
    # 3. The link the user clicks in the email
    path(
        'reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), 
        name='password_reset_confirm'
    ),
    
    # 4. Success page after password change
    path(
        'reset/done/', 
        auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), 
        name='password_reset_complete'
    ),
    
    # ... other student URLs
]