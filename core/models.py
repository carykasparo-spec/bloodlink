import random
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


BLOOD_TYPES = [
    ('A+', 'A+'), ('A-', 'A-'),
    ('B+', 'B+'), ('B-', 'B-'),
    ('AB+', 'AB+'), ('AB-', 'AB-'),
    ('O+', 'O+'), ('O-', 'O-'),
]

BADGE_TIERS = [
    ('none', 'No Badge'),
    ('first_drop', '🩸 First Drop'),
    ('helper', '💪 Helper'),
    ('lifesaver', '❤️ Lifesaver'),
    ('hero', '🦸 Hero'),
    ('champion', '🏆 Champion'),
    ('life_champion', '👑 Life Champion'),
]


class DonorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='donor_profile')
    blood_type = models.CharField(max_length=5, choices=BLOOD_TYPES)
    phone = models.CharField(max_length=15, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    bio = models.TextField(blank=True)
    badge = models.CharField(max_length=20, choices=BADGE_TIERS, default='none')
    phone_verified = models.BooleanField(default=False)
    # Health declarations
    has_hiv          = models.BooleanField(default=False)
    has_diabetes     = models.BooleanField(default=False)
    has_sugar        = models.BooleanField(default=False)
    has_skin_disease = models.BooleanField(default=False)
    covid_vaccinated  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def donation_count(self):
        return self.user.donations.count()

    def update_badge(self):
        count = self.donation_count()
        if count >= 20:
            self.badge = 'life_champion'
        elif count >= 15:
            self.badge = 'champion'
        elif count >= 10:
            self.badge = 'hero'
        elif count >= 5:
            self.badge = 'lifesaver'
        elif count >= 3:
            self.badge = 'helper'
        elif count >= 1:
            self.badge = 'first_drop'
        else:
            self.badge = 'none'
        self.save()

    def badge_display(self):
        return dict(BADGE_TIERS).get(self.badge, '')

    def __str__(self):
        return f"{self.user.username} ({self.blood_type})"


# ── OTP Verification ──────────────────────────────────────────────────────────
class OTPVerification(models.Model):
    """Stores a one-time password tied to a phone number.

    A new record is created every time an OTP is sent.
    Old / expired records are safe to delete at any time.
    """
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    # OTP expires after 10 minutes
    OTP_EXPIRY_MINUTES = 10

    @classmethod
    def generate_for(cls, phone: str) -> 'OTPVerification':
        """Create a fresh 6-digit OTP for *phone* (invalidates old ones)."""
        cls.objects.filter(phone=phone, is_used=False).update(is_used=True)
        code = str(random.randint(100000, 999999))
        return cls.objects.create(phone=phone, code=code)

    def is_valid(self) -> bool:
        """True if not used and not expired."""
        if self.is_used:
            return False
        expiry = self.created_at + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        return timezone.now() <= expiry

    def __str__(self):
        return f"OTP {self.code} for {self.phone}"


class DonationRecord(models.Model):
    donor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations')
    date = models.DateField()
    location = models.CharField(max_length=200)
    units = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    photo = models.ImageField(upload_to='donation_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.donor.username} — {self.date}"


class BloodRequest(models.Model):
    STATUS = [('open', 'Open'), ('fulfilled', 'Fulfilled'), ('closed', 'Closed')]

    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blood_requests')
    blood_type = models.CharField(max_length=5, choices=BLOOD_TYPES)
    units_needed = models.PositiveIntegerField(default=1)
    hospital = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=15)
    urgency = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High! Urgent')],
        default='medium'
    )
    status = models.CharField(max_length=10, choices=STATUS, default='open')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.blood_type} needed at {self.hospital}"


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender} → {self.receiver}: {self.content[:40]}"


class GalleryPhoto(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='gallery/')
    event_date = models.DateField(blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title
