from django.urls import path
from . import views

urlpatterns = [
    # Landing Auth Page
    path("auth/", views.auth_page, name="auth_page"),

    # Student Auth
    path("student/signup/", views.student_signup, name="student_signup"),
    path("student/login/", views.student_login, name="student_login"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),

    # Instructor Auth
    path("instructor/signup/", views.instructor_signup, name="instructor_signup"),
    path("instructor/login/", views.instructor_login, name="instructor_login"),
    path("instructor/dashboard/", views.instructor_dashboard, name="instructor_dashboard"),

    # Admin Dashboard (keep separate for role-based routing)
    path("admin/dashboard/", views.admin_dashboard, name="admin_dashboard"),

    # Logout (works for all roles)
    path("logout/", views.logout_view, name="logout"),
    path("home/", views.home, name="home"),
]
