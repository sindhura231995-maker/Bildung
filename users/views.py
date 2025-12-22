from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from courses.utils import check_and_send_reminders

# Use only your custom User model
from .models import User, Profile, LoginHistory, InstructorProfile
from .forms import StudentSignUpForm, InstructorSignUpForm, ProfileForm, UserDisplayForm, InstructorUserReadOnlyForm, InstructorUserForm, InstructorProfileForm
from courses.models import Course, Enrollment, Notification

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
            if hasattr(user, 'role') and user.role == "student":
                login(request, user)
                record_login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                return redirect("student_dashboard")
            else:
                messages.error(request, "This login is only for students.")
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()
    return render(request, "users/student_login.html", {"form": form})

# --- Instructor Login ---
def instructor_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if hasattr(user, 'role') and user.role == "instructor":
                login(request, user)
                record_login(request, user)
                return redirect("instructor:instructor_dashboard")
            else:
                messages.error(request, "This login is only for instructors.")
    else:
        form = AuthenticationForm()
    return render(request, "users/instructor_login.html", {"form": form})

def logout_view(request):
    record_logout(request)
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect("auth_page")

# ---  Password Reset ---
def custom_password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        # Check if user exists with this email
        try:
            user = User.objects.get(email=email)
            
            # Generate token and send email
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset URL
            reset_url = f"{request.scheme}://{request.get_host()}/password-reset-confirm/{uid}/{token}/"
            
            # Determine user role for email content
            user_role = user.role if hasattr(user, 'role') else 'user'
            
            # Send email
            subject = f"Password Reset Request - Bildung Platform"
            message = f"""
Hello {user.username},

You're receiving this email because you requested a password reset for your {user_role} account.

Please click the link below to reset your password:
{reset_url}

If you didn't request this reset, please ignore this email.

Thanks,
The Bildung Platform Team
"""
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                return redirect('password_reset_sent')
                
            except Exception as e:
                # If email fails, still redirect to success page for security
                print(f"Email sending failed: {e}")
                return redirect('password_reset_sent')
            
        except User.DoesNotExist:
            # Still show success message for security (don't reveal if email exists)
            return redirect('password_reset_sent')
    
    return render(request, 'forgot_password.html')

def password_reset_sent(request):
    return render(request, 'password_reset_sent.html')

# --- Password Reset Confirm ---
def custom_password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        
        if default_token_generator.check_token(user, token):
            if request.method == 'POST':
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')
                
                if new_password and len(new_password) >= 8:
                    if new_password == confirm_password:
                        user.set_password(new_password)
                        user.save()
                        messages.success(request, 'Your password has been reset successfully! You can now login with your new password.')
                        
                        # SMART REDIRECT: Send users to appropriate login based on their role
                        if hasattr(user, 'role'):
                            if user.role == 'instructor':
                                return redirect('instructor_login')
                            elif user.role == 'student':
                                return redirect('student_login')
                        
                        # Default fallback
                        return redirect('auth_page')
                    else:
                        messages.error(request, 'Passwords do not match.')
                else:
                    messages.error(request, 'Password must be at least 8 characters long.')
            
            return render(request, 'password_reset_confirm.html')
        else:
            messages.error(request, 'Invalid or expired reset link.')
            return redirect('auth_page')
            
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        messages.error(request, 'Invalid reset link.')
        return redirect('auth_page')

@login_required
def student_dashboard(request):
    if request.user.role != "student":
        messages.error(request, "Access denied. Student area only.")
        return redirect("login")
    check_and_send_reminders(request.user)
    all_courses = Course.objects.all()

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    unread_notifications = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by("-created_at")[:5]
    enrolled_course_ids = Enrollment.objects.filter(
        student=request.user
    ).values_list("course_id", flat=True)

    return render(request, "courses/student/student_dashboard.html", {
        "all_courses": all_courses,
        "unread_count": unread_count,
        "unread_notifications": unread_notifications,
        "enrolled_course_ids": enrolled_course_ids,
    })


@login_required(login_url="/auth/")
def admin_dashboard(request):
    if not hasattr(request.user, 'role') or request.user.role != "admin":
        messages.error(request, "Access denied. Admin area only.")
        return redirect("auth_page")
    return render(request, "admin/dashboard.html")

@login_required
def post_login_redirect_view(request):
    user = request.user
    if not hasattr(user, 'role'):
        messages.error(request, "User role not defined.")
        return redirect("auth_page")
    
    if user.role == "student":
        record_login(request, user)
        return redirect("student_dashboard")
    elif user.role == "instructor":
        record_login(request, user)
        return redirect("instructor:instructor_dashboard")
    elif user.role == "admin":
        record_login(request, user)
        return redirect("admin_dashboard")
    else:
        return redirect("auth_page")

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

    if request.method == 'POST' and is_editing:
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        user_form = UserDisplayForm(request.POST, instance=request.user) 

        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile_view') 
        
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


@login_required
def instructor_profile_view_or_edit(request, mode=None):

    try:
        profile = request.user.instructor_profile
    except InstructorProfile.DoesNotExist:
        profile = InstructorProfile.objects.create(user=request.user)

    is_editing = (mode == "edit")

    if request.method == "POST" and is_editing:

        user_form = InstructorUserForm(request.POST, instance=request.user)
        profile_form = InstructorProfileForm(request.POST, request.FILES, instance=profile)

        if profile_form.is_valid() and user_form.is_valid():
            user_form.save()
            profile_form.save()

            messages.success(request, "Profile updated successfully!")
            return redirect("instructor_profile_view")
    else:
        if is_editing:
            user_form = InstructorUserForm(instance=request.user)
        else:
            user_form = InstructorUserReadOnlyForm(instance=request.user)

        profile_form = InstructorProfileForm(instance=profile)

    context = {
        "profile": profile,
        "user_form": user_form,
        "profile_form": profile_form,
        "is_editing": is_editing,
    }

    return render(request, "instructor/instructor_profile.html", context)


# --- Google OAuth Entry ---
def google_oauth_entry(request):
    """Capture ?type=student/instructor before sending to Google OAuth."""
    role = request.GET.get('type', '').strip()
    next_url = request.GET.get('next', '/google-redirect/').strip()

    if role:
        request.session['google_role'] = role  

    redirect_url = f"/social-auth/login/google-oauth2/?next={next_url}&prompt=select_account"
    return redirect(redirect_url)

# --- Google OAuth Redirect ---
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
    

def record_login(request, user):
    LoginHistory.objects.create(
        user=user,
        login_time=timezone.now(),
        status="Success",
        device=request.META.get('HTTP_USER_AGENT', 'Unknown Device')
    )


def record_logout(request):
    if request.user.is_authenticated:
        last_login_entry = LoginHistory.objects.filter(
            user=request.user,
            logout_time__isnull=True
        ).order_by('-login_time').first()

        if last_login_entry:
            last_login_entry.logout_time = timezone.now()
            last_login_entry.save()
