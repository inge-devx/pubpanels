from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Sécurité / environnement
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-change-this-in-production"
)

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost,*"

).split(",")

# Applications installées
INSTALLED_APPS = [
    "django.contrib.gis",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core.apps.CoreConfig",
    "apps.users.apps.UsersConfig",
    "apps.agencies.apps.AgenciesConfig",
    "apps.panels.apps.PanelsConfig",
    "apps.reservations.apps.ReservationsConfig",
    "apps.locations.apps.LocationsConfig",
    "apps.geography.apps.GeographyConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "src.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.active_agency",
            ],
        },
    },
]

WSGI_APPLICATION = "src.wsgi.application"

# Base de données
"""DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}"""

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",  # Moteur géographique
        "NAME": "pubpanel_db",            # Le nom de la base que vous créez dans pgAdmin
        "USER": "postgres",                # L'utilisateur par défaut de PostgreSQL
        "PASSWORD": "postgres",  # Le mot de passe choisi à l'installation
        "HOST": "127.0.0.1",               # Signifie "sur mon ordinateur"
        "PORT": "5432",                    # Le port par défaut
    }
}


# Validation des mots de passe
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalisation
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Ouagadougou"
USE_I18N = True
USE_TZ = True

# Fichiers statiques
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Fichiers médias locaux par défaut (pour le développement classique)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# --- CONFIGURATION SÉCURISÉE CLOUDFLARE R2 PRODUCTION ---
CLOUDFLARE_R2_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")

if CLOUDFLARE_R2_ACCESS_KEY:
    # Si les clés sont détectées (en production sur le serveur), on active le Cloud
    AWS_ACCESS_KEY_ID = CLOUDFLARE_R2_ACCESS_KEY
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")

    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "endpoint_url": AWS_S3_ENDPOINT_URL,
                "signature_version": "s3v4",
                "file_overwrite": False,
                "default_acl": None,
            }
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
else:
    # Si aucune clé n'est configurée (votre quotidien en local sur votre PC),
    # Django enregistre sagement les photos dans votre dossier local /media/
    pass

# Clé primaire par défaut
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

LOGIN_REDIRECT_URL = "action_center"
LOGOUT_REDIRECT_URL = "home"

# Email configuration (MVP)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@pubpanels.local"

# Configuration des bibliothèques géographiques (Spécifique Windows)
import os

if os.name == 'nt':  # Vérifie si l'ordinateur tourne sous Windows
    # On indique le chemin vers le dossier OSGeo4W que nous venons d'installer
    OSGEO4W_ROOT = r"C:\OSGeo4W"

    # On ajoute le dossier des binaires aux chemins système de Python
    os.environ['PATH'] = os.path.join(OSGEO4W_ROOT, 'bin') + os.path.pathsep + os.environ['PATH']

    # On indique directement les fichiers précis de GDAL et PROJ à Django
    GDAL_LIBRARY_PATH = os.path.join(OSGEO4W_ROOT, 'bin', 'gdal313.dll')  # Le script s'adaptera automatiquement
    PROJ_LIB = os.path.join(OSGEO4W_ROOT, 'share', 'proj')
