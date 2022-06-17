from django.urls import path

from tests.django.myapp.views import broken_view

urlpatterns = [path("broken", broken_view)]
