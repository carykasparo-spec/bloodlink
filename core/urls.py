from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('donors/', views.search_donors, name='search_donors'),
    path('history/', views.donation_history, name='donation_history'),
    path('history/certificate/<int:donation_id>/', views.download_certificate, name='download_certificate'),
    path('request/', views.request_blood, name='request_blood'),
    path('inbox/', views.inbox, name='inbox'),
    path('inbox/<int:user_id>/', views.conversation, name='conversation'),
    path('gallery/', views.gallery, name='gallery'),
    path('api/chat/', views.ai_chat, name='ai_chat'),

    # ── OTP / SMS ──────────────────────────────────────────
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('login-otp/', views.login_otp_view, name='login_otp'),
]
