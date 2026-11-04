from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent
ON_VERCEL = os.getenv('VERCEL') == '1'
DEBUG = os.getenv('DJANGO_DEBUG', '0' if ON_VERCEL else '1') == '1'
if ON_VERCEL and DEBUG:
    raise RuntimeError('Debug mode is not permitted on Vercel')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError('DJANGO_SECRET_KEY is required in production')
    key_file = BASE_DIR / '.local-secret'
    if not key_file.exists():
        import secrets
        key_file.write_text(secrets.token_urlsafe(64))
        key_file.chmod(0o600)
    SECRET_KEY = key_file.read_text().strip()
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')
if ON_VERCEL:
    # Trust only hostnames attached to this deployment, never a wildcard Vercel domain.
    ALLOWED_HOSTS += [os.environ[k] for k in ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL') if os.getenv(k)]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = [x for x in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if x]
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','community']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware','community.middleware.RateLimitMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','community.context.shell']}}]
WSGI_APPLICATION = 'config.wsgi.application'
if os.getenv('DATABASE_URL'):
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(os.environ['DATABASE_URL'], conn_max_age=0, ssl_require=ON_VERCEL)}
    if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        raise RuntimeError('DATABASE_URL must point to PostgreSQL')
    # A shared SQLite filesystem cannot persist across Vercel function instances.
elif ON_VERCEL:
    raise RuntimeError('A persistent PostgreSQL DATABASE_URL is required on Vercel')
else:
    DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3','OPTIONS':{'timeout':30,'transaction_mode':'IMMEDIATE'}}}
STORAGES = {'default': {'BACKEND': 'community.storage.DatabasePrivateStorage' if ON_VERCEL else 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
# Keep raster uploads below Vercel's function request/response payload limit.
MAX_IMAGE_BYTES = 3 * 1024 * 1024 if ON_VERCEL else 5 * 1024 * 1024
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR/'static']
STATIC_ROOT = BASE_DIR/'staticfiles'
MEDIA_ROOT = BASE_DIR/'private-media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/welcome/'
EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND','django.core.mail.backends.filebased.EmailBackend')
EMAIL_FILE_PATH = BASE_DIR/'local-mail'
if ON_VERCEL and EMAIL_BACKEND == 'django.core.mail.backends.filebased.EmailBackend':
    raise RuntimeError('Configure an email delivery backend on Vercel; local email files are not persistent')
EMAIL_HOST = os.getenv('EMAIL_HOST','localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT','587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL','TK-ZONE <noreply@localhost>')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# File-backed test database exercises the same writer locking as the development database.
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default']['TEST'] = {'NAME': BASE_DIR / 'test-db.sqlite3'}
