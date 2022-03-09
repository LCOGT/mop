from django.urls import path, include
from django.views.generic import TemplateView
from mop.views import TimeAllocView

urlpatterns = [
    path('', include('tom_common.urls')),
    path('time-alloc/', TimeAllocView.as_view(), name='time-alloc')
]
