import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'channels',
    'django_celery_beat',
    # Local apps
    'apps.app_server',
    'apps.srs',
    'apps.ai',
    'apps.les',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'memo_backend.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'memo_backend.wsgi.application'
ASGI_APPLICATION = 'memo_backend.asgi.application'

# Database – PostgreSQL is the primary database for all environments
DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('DB_NAME', 'memo_db'),
        'USER': os.getenv('DB_USER', 'memo_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'memo_password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.getenv('STATIC_ROOT', str(BASE_DIR / 'staticfiles'))
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.app_server.pagination.standard_pagination.StandardPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'EXCEPTION_HANDLER': 'apps.app_server.exceptions.exception_handler.custom_exception_handler',
}

# Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', '15'))
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', '7'))
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Channels – use Redis when available, fallback to in-memory for simple dev
REDIS_URL = os.getenv('REDIS_URL', '')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# AI Provider – switch between "openai" and "local" via env
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai')
AI_STT_PROVIDER = os.getenv('AI_STT_PROVIDER', '') or AI_PROVIDER
AI_TTS_PROVIDER = os.getenv('AI_TTS_PROVIDER', '') or AI_PROVIDER

# External API keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GOOGLE_AI_API_KEY = os.getenv('GOOGLE_AI_API_KEY', '')

# Model overrides (provider-specific defaults used if not set)
AI_LLM_MODEL = os.getenv('AI_LLM_MODEL', '')
AI_STT_MODEL = os.getenv('AI_STT_MODEL', '')
AI_TTS_MODEL = os.getenv('AI_TTS_MODEL', '')

# Local AI endpoints (used when AI_PROVIDER=local)
AI_LOCAL_LLM_URL = os.getenv('AI_LOCAL_LLM_URL', 'http://localhost:11434')
AI_LOCAL_LLM_MODEL = os.getenv('AI_LOCAL_LLM_MODEL', 'llama3')
AI_LOCAL_LLM_API_KEY = os.getenv('AI_LOCAL_LLM_API_KEY', '')
AI_LOCAL_LLM_TIMEOUT = int(os.getenv('AI_LOCAL_LLM_TIMEOUT', '60'))
AI_LOCAL_STT_URL = os.getenv('AI_LOCAL_STT_URL', 'http://localhost:8081')
AI_LOCAL_STT_MODEL = os.getenv('AI_LOCAL_STT_MODEL', 'whisper-large-v3')
AI_LOCAL_STT_TIMEOUT = int(os.getenv('AI_LOCAL_STT_TIMEOUT', '60'))
AI_LOCAL_TTS_URL = os.getenv('AI_LOCAL_TTS_URL', 'http://localhost:8082')
AI_LOCAL_TTS_TIMEOUT = int(os.getenv('AI_LOCAL_TTS_TIMEOUT', '60'))

# RAG configuration
AI_RAG_ENABLED = os.getenv('AI_RAG_ENABLED', 'false').lower() in ('true', '1', 'yes')
AI_VECTOR_STORE = os.getenv('AI_VECTOR_STORE', 'chroma')
AI_VECTOR_STORE_PATH = os.getenv('AI_VECTOR_STORE_PATH', '')
AI_VECTOR_COLLECTION = os.getenv('AI_VECTOR_COLLECTION', 'memo_rag')
AI_RAG_TOP_K = int(os.getenv('AI_RAG_TOP_K', '5'))
AI_OLLAMA_EMBED_URL = os.getenv('AI_OLLAMA_EMBED_URL', 'http://host.docker.internal:11434')
AI_OLLAMA_EMBED_MODEL = os.getenv('AI_OLLAMA_EMBED_MODEL', 'nomic-embed-text')
AI_OLLAMA_EMBED_TIMEOUT = int(os.getenv('AI_OLLAMA_EMBED_TIMEOUT', '30'))

# Custom user model
AUTH_USER_MODEL = 'app_server.User'
