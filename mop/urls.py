"""django URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include

from mop.views import MOPTargetDetailView
from django.views.generic import TemplateView
import os

base_path = os.environ.get('URL_BASE_PATH', '').strip('/')
trailing_slash = ''
if base_path:
    trailing_slash = '/'
urlpatterns = [
    path(f'''{base_path}{trailing_slash}oidc/''', include('mozilla_django_oidc.urls')),
    path(f'''{base_path}{trailing_slash}targets/<int:pk>/''', MOPTargetDetailView.as_view(), name='detail'),
    path(f'''{base_path}{trailing_slash}''', TemplateView.as_view(
        template_name='tom_common/index.html',
        extra_context={"base_path": base_path}), name='home'),
    path(f'''{base_path}{trailing_slash}''', include('tom_common.urls')),
]
