from django.urls import path
from .views import LoginView, LogoutView, UserView

urlpatterns = [
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('auth/user', UserView.as_view(), name='user'),
]
