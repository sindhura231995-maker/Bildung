from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm

from .forms import StudentSignUpForm, InstructorSignUpForm
from courses.models import Course


# --- Auth Landing Page (just options, no forms) ---
def auth_page(request):
    return render(request, "users/auth_page.html")


# --- Student Signup ---
def student_signup(request):
    if request.method == "POST":
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = "student"
            user.save()
            login(request, user)
            return redirect("student_dashboard")
    else:
        form = StudentSignUpForm()
    return render(request, "users/student_signup.html", {"form": form})


# --- Instructor Signup ---
def instructor_signup(request):
    if request.method == "POST":
        form = InstructorSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = "instructor"
            user.save()
            login(request, user)
            return redirect("instructor_dashboard")
    else:
        form = InstructorSignUpForm()
    return render(request, "users/instructor_signup.html", {"form": form})


# --- Student Login ---
def student_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == "student":
                login(request, user)
                return redirect("student_dashboard")
            else:
                messages.error(request, "This login is only for students.")
    else:
        form = AuthenticationForm()
    return render(request, "users/student_login.html", {"form": form})


# --- Instructor Login ---
def instructor_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role == "instructor":
                login(request, user)
                return redirect("instructor_dashboard")
            else:
                messages.error(request, "This login is only for instructors.")
    else:
        form = AuthenticationForm()
    return render(request, "users/instructor_login.html", {"form": form})


# --- Logout (works for all roles) ---
def logout_view(request):
    logout(request)
    return redirect("auth_page")


# --- Dashboards ---
@login_required(login_url="/auth/")
def student_dashboard(request):
    if request.user.role != "student":
        return redirect("auth_page")
    enrolled_courses = Course.objects.filter(enrollments__student=request.user)
    return render(request, "courses/student_dashboard.html", {"enrolled_courses": enrolled_courses})


@login_required(login_url="/auth/")
def instructor_dashboard(request):
    if request.user.role != "instructor":
        return redirect("auth_page")
    courses = Course.objects.filter(instructor=request.user)
    return render(request, "courses/instructor_dashboard.html", {"courses": courses})


@login_required(login_url="/auth/")
def admin_dashboard(request):
    if request.user.role != "admin":
        return redirect("auth_page")
    return render(request, "admin/dashboard.html")

def home(request):
    return render(request, "base.html")  
