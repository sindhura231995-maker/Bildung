from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    # Landing / Auth
    path("auth/", views.auth_page, name="auth_page"),

    # Student
    path("student/signup/", views.student_signup, name="student_signup"),
    path("student/login/", views.student_login, name="student_login"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    # Student course-related URLs (namespaced)
    #path("student/", include(("courses.student_urls", "student"), namespace="student")),
    path("student/", include(("courses.student_urls", "student_courses"), namespace="student_courses")),

    # Password reset
    path(
        'password-reset/', 
        auth_views.PasswordResetView.as_view(template_name='password_reset.html'), 
        name='password_reset'
    ),
    path(
        'password-reset/done/', 
        auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), 
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/', 
        auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), 
        name='password_reset_confirm'
    ),

    path(
        'accounts/reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset_complete.html"
        ),
        name='password_reset_complete'
    ),

    # Instructor
    path("instructor/signup/", views.instructor_signup, name="instructor_signup"),
    path("instructor/login/", views.instructor_login, name="instructor_login"),
    
    # Include all instructor dashboard & course URLs
    path("instructor/", include(("courses.instructor_urls", "instructor"), namespace="instructor")),
    path('instructor/dashboard/', views.instructor_dashboard, name='instructor_dashboard'),

    # Admin
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Logout
    path("logout/", views.logout_view, name="logout_view"),

    # Post-login redirect
    path("post-login/", views.post_login_redirect, name="post_login_redirect"),

    # Added Google OAuth Routes (Only Addition)
    path("social-auth/", include("social_django.urls", namespace="social")),
    path("google/login/", views.google_oauth_entry, name="google_oauth_entry"),
    path("google-redirect/", views.google_login_redirect, name="google_login_redirect"),
]
