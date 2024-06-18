import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "fake-key"

INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_extensions',
    'guardian',
    'tom_common',
    'django_comments',
    'bootstrap4',
    'crispy_bootstrap4',
    'crispy_forms',
    'django_filters',
    'django_gravatar',
    'rest_framework',
    'rest_framework.authtoken',
    'tom_targets',
    'tom_alerts',
    'tom_catalogs',
    'tom_observations',
    'tom_dataproducts',
    'mop',
    "tests",
    'microlensing_targets'
]

DATA_PRODUCT_TYPES = {
    'photometry': ('photometry', 'Photometry'),
    'fits_file': ('fits_file', 'FITS File'),
    'spectroscopy': ('spectroscopy', 'Spectroscopy'),
    'image_file': ('image_file', 'Image File'),
    'TAP_priority': ('TAP_priority', 'TAP Priority'),
    'lc_model': ('lc_model', 'Model'),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tom_common.middleware.ExternalServiceMiddleware',
]

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
            ],
        },
    },
]

EXTRA_FIELDS = [{'name':'Alive','type':'boolean', 'default':True},
                {'name':'Classification','type':'string','default':'Microlensing PSPL'},
                {'name':'Category','type':'string','default':'Microlensing stellar/planet'},
                {'name':'Observing_mode','type':'string','default':'No'},
                {'name':'t0','type':'number','default':0},
                {'name':'u0','type':'number','default':0},
                {'name':'tE','type':'number','default':0},
                {'name':'piEN','type':'number','default':0},
                {'name':'piEE','type':'number','default':0},
                {'name':'rho','type':'number','default':0},
                {'name':'s','type':'number','default':0},
                {'name':'q','type':'number','default':0},
                {'name':'alpha','type':'number','default':0},
                {'name':'Source_magnitude','type':'number','default':0},
                {'name':'Blend_magnitude','type':'number','default':0},
                {'name':'Baseline_magnitude','type':'number','default':0},
                {'name':'Fit_covariance','type':'string','default':''},
                {'name':'TAP_priority','type':'number','default':''},
                {'name':'TAP_priority_longtE','type':'number','default':''},
                {'name':'Spectras','type':'number','default':0},
                {'name':'Last_fit','type':'number','default':2446756.50000},
                {'name':'chi2','type':'number','default':99999.9999},
                {'name':'red_chi2','type':'number','default':99999.9999},
                {'name':'KS_test','type':'number','default':0},
                {'name':'SW_test','type':'number','default':0},
                {'name':'AD_test','type':'number','default':0},
                {'name':'Latest_data_HJD','type':'number','default':0},
                {'name':'Latest_data_UTC','type':'datetime','default':''}]

TARGET_MODEL_CLASS = 'microlensing_targets.models.MicrolensingTarget'

TARGET_PERMISSIONS_ONLY=True

FACILITIES = {
    'LCO': {
        'portal_url': 'https://observe.lco.global',
        'api_key': os.environ.get('LCO_API_KEY','dummy'),
    },
}

TOM_FACILITY_CLASSES = [
    'tom_observations.facilities.lco.LCOFacility',
    'tom_observations.facilities.gemini.GEMFacility',
    'tom_observations.facilities.soar.SOARFacility',
    'tom_observations.facilities.lt.LTFacility'
]

HOOKS = {
    'target_post_save': 'tom_common.hooks.target_post_save',
    'observation_change_state': 'tom_common.hooks.observation_change_state',
    'data_product_post_upload': 'tom_dataproducts.hooks.data_product_post_upload'
}

try:
    from local_settings import * # noqa
except ImportError:
    pass
