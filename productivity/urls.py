from django.urls import path, include
from django.views.generic import TemplateView
from mop.views import ProductivityView

urlpatterns = [
    path('', include('tom_common.urls')),
    path('productivity/', ProductivityView.as_view(), name='productivity')
]
