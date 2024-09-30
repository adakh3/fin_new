from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.upload_file_view, name='home'),  # Changed to 'home'
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html', next_page='home'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('quickbooks_report_analysis/', views.quickbooks_report_analysis, name='quickbooks_report_analysis'),
    path('quickbooks/callback/', views.quickbooks_callback, name='quickbooks_callback'),
    path('start_quickbooks_auth/', views.start_quickbooks_auth, name='start_quickbooks_auth'),
    path('quickbooks_chat/', views.quickbooks_chat, name='quickbooks_chat'),
]