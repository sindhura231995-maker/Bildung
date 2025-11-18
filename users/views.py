from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from .models import User, Profile
from .forms import StudentSignUpForm, InstructorSignUpForm, ProfileForm, UserDisplayForm
from courses.models import Course, Enrollment
from django.core.mail import send_mail
from django.conf import settings
# Added for Google OAuth
from urllib.parse import urlparse, parse_qs
from django.contrib.auth.backends import ModelBackend


def auth_page(request):
    return render(request, "users/auth_page.html")


# --- Student Signup ---

def student_signup(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Welcome {user.first_name}! Your account has been created.")
            return redirect('student_dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = StudentSignUpForm()
    return render(request, 'users/student_signup.html', {'form': form})
# --- Instructor Signup ---
  

def instructor_signup(request):
    if request.method == 'POST':
        form = InstructorSignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'instructor'

            raw_password = form.cleaned_data.get("password1") or form.cleaned_data.get("password")
            if raw_password:
                user.set_password(raw_password)
            user.save()

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect("instructor:instructor_dashboard")
    else:
        form = InstructorSignUpForm()

    return render(request, 'users/instructor_signup.html', {'form': form})



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
                return redirect("instructor:instructor_dashboard")
            else:
                messages.error(request, "This login is only for instructors.")
    else:
        form = AuthenticationForm()
    return render(request, "users/instructor_login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("auth_page")


# --- Dashboards ---
def student_dashboard(request):
    if request.user.role != "student":
        return redirect("login")
    all_courses = Course.objects.all()
    enrolled_courses = Course.objects.filter(students=request.user)
    return render(request, 'courses/student_dashboard.html', {
        'all_courses': all_courses,
        'enrolled_courses': enrolled_courses
    })

@login_required(login_url="/auth/")
def admin_dashboard(request):
    if request.user.role != "admin":
        return redirect("auth_page")
    return render(request, "admin/dashboard.html")



@login_required
def post_login_redirect_view(request):
    user = request.user
    if user.role == "student":
        return redirect("student_dashboard")
    elif user.role == "instructor":
        return redirect("instructor:instructor_dashboard")
    elif user.role == "admin":
        return redirect("admin_dashboard")
    else:
        return redirect("guest_home")  # fallback


def signup_view(request):
    """
    Handles user registration and sends a welcome email.
    The email content will be printed to the terminal because of the
    'console.EmailBackend' setting in settings.py.
    """
    if request.method == 'POST':
        # --- 1. SIMULATE FORM PROCESSING AND USER CREATION ---
        # In a real app, you would validate the form data here.
        username = request.POST.get('username')
        email = request.POST.get('email')

        # Dummy checks for demonstration
        if not username or not email:
            return render(request, 'signup.html', {'error': 'Please fill in both fields.'})

        try:
            # Simulate user creation (replace with actual User.objects.create_user)
            user = User(username=username, email=email)
            user.save()

            # --- 2. SEND WELCOME EMAIL ---
            send_mail(
                subject="Welcome to Bildung!",
                message=f"Hi {username}, thanks for signing up!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
        except Exception as e:
            return render(request, 'signup.html', {'error': str(e)})

    return render(request, 'signup.html')



@login_required
def profile_view_or_edit(request, mode=None):
    """
    Handles both displaying the profile (default) and editing ONLY Profile fields.
    """
    
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)

    is_editing = (mode == 'edit')
    
    # 1. Handle POST Request (Form Submission)
    if request.method == 'POST' and is_editing:
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserDisplayForm(request.POST, instance=request.user) 

        if profile_form.is_valid():
            # Only save the Profile form
            profile_form.save()
            
            # Redirect to the non-edit/detail view after successful save
            return redirect('profile_view') 
        
    # 2. Handle GET Request (Initial Load or Load with Errors)
    else:
        user_form = UserDisplayForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)

    context = {
        'profile': profile,
        'user_form': user_form,       # Read-only user form
        'profile_form': profile_form, # Editable profile form
        'is_editing': is_editing,
    }
    return render(request, 'student/student_profile.html', context)

# --- Google OAuth Entry (added) ---
def google_oauth_entry(request):
    """Capture ?type=student/instructor before sending to Google OAuth."""
    role = request.GET.get('type', '').strip()
    next_url = request.GET.get('next', '/google-redirect/').strip()

    if role:
        request.session['google_role'] = role  # Save role temporarily in session

    redirect_url = f"/social-auth/login/google-oauth2/?next={next_url}&prompt=select_account"
    return redirect(redirect_url)


# --- Google OAuth Redirect (added) ---
@login_required
def google_login_redirect(request):
    """Redirect Google-authenticated users to their appropriate dashboards."""
    user = request.user
    role_param = request.GET.get('type') or request.session.get('google_role')

    if role_param:
        request.session['google_role'] = role_param

        if role_param == 'instructor' and user.role != 'instructor':
            user.role = 'instructor'
            user.save()
        elif role_param == 'student' and user.role != 'student':
            user.role = 'student'
            user.save()

    if user.role == 'instructor':
        return redirect('instructor:instructor_dashboard')
    elif user.role == 'student':
        return redirect('student_dashboard')
    else:
        return redirect('auth_page')