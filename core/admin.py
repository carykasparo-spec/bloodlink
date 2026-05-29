from django.contrib import admin
from .models import DonorProfile, DonationRecord, BloodRequest, Message, GalleryPhoto


@admin.register(DonorProfile)
class DonorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'blood_type', 'city', 'state', 'is_available', 'badge']
    list_filter = ['blood_type', 'is_available', 'badge']
    search_fields = ['user__username', 'city', 'state']


@admin.register(DonationRecord)
class DonationRecordAdmin(admin.ModelAdmin):
    list_display = ['donor', 'date', 'location', 'units']
    list_filter = ['date']
    search_fields = ['donor__username', 'location']


@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display = ['requester', 'blood_type', 'hospital', 'city', 'urgency', 'status']
    list_filter = ['blood_type', 'urgency', 'status']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'timestamp', 'is_read']


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_date', 'uploaded_by', 'is_featured', 'uploaded_at']
    list_filter = ['is_featured']
    search_fields = ['title']
