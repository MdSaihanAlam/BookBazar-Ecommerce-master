import os
from decouple import config, Csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Override any of these with environment variables or a .env file in production.
SECRET_KEY = config('SECRET_KEY', default='=251om_=%8c-y2e$h&qiw!56_5!@$ol1a(=_%j2l=roubv1m*u')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'eco.apps.EcoConfig',
    'users.apps.UsersConfig',

    'django_countries',
    'crispy_forms',
    'crispy_bootstrap4',
    'mptt',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'eco.middleware.UserLanguageMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'abcd.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'eco.context_processors.cart_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'abcd.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': config('DATABASE_PATH', default=os.path.join(BASE_DIR, 'db.sqlite3')),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True

# Languages the site is translated into; a profile language outside this list falls back to English.
LANGUAGES = [
    ('en', 'English'),
    ('bn', 'বাংলা'),
]
LOCALE_PATHS = [os.path.join(BASE_DIR, 'locale')]
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

AUTH_USER_MODEL = 'users.CustomUser'
LOGIN_URL = '/users/login/'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap4'
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Emails are printed to the console unless an SMTP backend is configured.
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='BookBazar <noreply@bookbazar.local>')
CONTACT_EMAIL = config('CONTACT_EMAIL', default='support@bookbazar.local')

# Stripe test keys; set real keys through the environment.
STRIPE_PUBLIC_KEY = config('STRIPE_PUBLIC_KEY', default='pk_test_51HHON9JPYmkoAsB01yYUI288THzt2kKmjqu8BdzUePai7grGYVZfUKT3l3mezN15lGo4Zh8yHdFx0i4PSGChrwh800wK4Tgtmz')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='sk_test_51HHON9JPYmkoAsB0R80Mtvq8Bmd7G252UDuO9uCL0zFKKEbtM2RNqJOqXrmmqLEHyfE3CxuqOIMFkoB36t1QX5wM005bBFDEvI')

# Prices are stored and charged in US dollars. Other currencies are shown using these
# fixed rates (units per 1 USD); update them, or set them through the environment.
CURRENCIES = {
    'usd': {'symbol': '$', 'rate': 1.0, 'decimals': 2},
    'eur': {'symbol': '€', 'rate': config('RATE_EUR', default=0.86, cast=float), 'decimals': 2},
    'gbp': {'symbol': '£', 'rate': config('RATE_GBP', default=0.75, cast=float), 'decimals': 2},
    'bdt': {'symbol': '৳', 'rate': config('RATE_BDT', default=122.0, cast=float), 'decimals': 0},
}

SESSION_COOKIE_AGE = 1209600  # 2 weeks
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://127.0.0.1:8000,http://localhost:8000', cast=Csv())

FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
