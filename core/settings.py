"""
Django settings for core project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-gu^1pt(^9a3gv=gw2jtq@q=q0r!%g1$ia+)msfttf$75dz54dt'
DEBUG = True

# ---------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Your apps
    'users',
    'courses',
    'quizzes',
    'forums',
    'chat',
    'home',

    # Third-party
    'channels',
    'subdomains',

    # Added for Google Login
    'social_django',
]

# ---------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------
MIDDLEWARE = [
    "subdomains.middleware.SubdomainURLRoutingMiddleware",  # MUST be first
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # Added for Google Login
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
            ],
        },
    },
]

# ---------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'bildung_db',
        'USER': 'root', # change with your MYSQL username
        'PASSWORD': ' ', # change with your MYSQL password
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ---------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'users.User'

LOGIN_URL = '/login/'
LOGOUT_REDIRECT_URL = '/'

# Added for Google Login
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',  # Google OAuth
    'django.contrib.auth.backends.ModelBackend',  # Default
)

SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = ' ' # Add your key  here
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = ' '  # Add your client secret here
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile']
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'prompt': 'select_account',
    'access_type': 'offline',
}

LOGIN_REDIRECT_URL = '/google-redirect/'  # After Google login redirect
LOGOUT_REDIRECT_URL = '/'

# ---------------------------------------------------------------------
# Subdomains
# ---------------------------------------------------------------------
ROOT_URLCONF = "core.urls"

SUBDOMAIN_URLCONFS = {
    None: "core.urls",  # main domain
    "admin": "users.admin_urls",
    "student": "users.student_urls",
    "instructor": "users.instructor_urls",
}

PARENT_HOST = "lvh.me"   # Needed for django-subdomains
ALLOWED_HOSTS = ['.lvh.me', 'lvh.me', '127.0.0.1', 'localhost']

# ---------------------------------------------------------------------
# Static & Media
# ---------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ---------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------
ASGI_APPLICATION = "core.asgi.application"
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

# ---------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_REDIRECT_URL = '/accounts/post-login/'
SITE_ID = 1

#password_reset_mail local
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

#password_reset_mail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'antharisaiteja@gmail.com'
EMAIL_HOST_PASSWORD ='viybdcfqakmylkus'
DEFAULT_FROM_EMAIL = 'Bildung Platform <antharisaiteja@gmail.com>'
