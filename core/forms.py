from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import DonorProfile, DonationRecord, BloodRequest, GalleryPhoto

BLOOD_TYPES = [
    ('A+', 'A+'), ('A-', 'A-'),
    ('B+', 'B+'), ('B-', 'B-'),
    ('AB+', 'AB+'), ('AB-', 'AB-'),
    ('O+', 'O+'), ('O-', 'O-'),
]


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    blood_type = forms.ChoiceField(choices=BLOOD_TYPES)
    # Phone is required so OTP can be sent
    phone = forms.CharField(
        max_length=15,
        required=True,
        help_text='Include country code, e.g. +919876543210',
    )
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)

    # Health condition declarations
    has_hiv = forms.BooleanField(
        required=False,
        label='I have / had HIV/AIDS',
    )
    has_diabetes = forms.BooleanField(
        required=False,
        label='I have Diabetes',
    )
    has_sugar = forms.BooleanField(
        required=False,
        label='I have high Blood Sugar',
    )
    has_skin_disease = forms.BooleanField(
        required=False,
        label='I have a Skin Disease',
    )
    covid_vaccinated = forms.BooleanField(
        required=False,
        label='I am COVID-19 Vaccinated',
    )

    # Terms & Conditions
    terms = forms.BooleanField(
        required=True,
        label='I agree to the Terms & Conditions',
        error_messages={'required': 'You must accept the Terms & Conditions to register.'},
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=50, required=False)
    last_name = forms.CharField(max_length=50, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = DonorProfile
        fields = ['blood_type', 'phone', 'city', 'state', 'is_available', 'avatar', 'latitude', 'longitude', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3}),
        }


class OTPVerifyForm(forms.Form):
    """Used on the /verify-otp/ page."""
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label='Enter 6-digit OTP',
        widget=forms.TextInput(attrs={
            'placeholder': '______',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}',
        }),
    )


class DonationForm(forms.ModelForm):
    class Meta:
        model = DonationRecord
        fields = ['date', 'location', 'units', 'notes', 'photo']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class BloodRequestForm(forms.ModelForm):
    class Meta:
        model = BloodRequest
        fields = ['blood_type', 'units_needed', 'hospital', 'city', 'contact_phone', 'urgency', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }


class DonorSearchForm(forms.Form):
    blood_type = forms.ChoiceField(
        choices=[('', 'Any Blood Type')] + BLOOD_TYPES,
        required=False
    )
    city = forms.CharField(max_length=100, required=False)


class GalleryUploadForm(forms.ModelForm):
    class Meta:
        model = GalleryPhoto
        fields = ['title', 'description', 'image', 'event_date', 'is_featured']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
            'event_date': forms.DateInput(attrs={'type': 'date'}),
        }
