import json
import os
import io
import urllib.request
import urllib.error
import traceback
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db.models import Q

from .models import DonorProfile, DonationRecord, BloodRequest, Message, GalleryPhoto, OTPVerification
from .forms import (
    RegisterForm, ProfileForm, DonationForm, BloodRequestForm,
    DonorSearchForm, GalleryUploadForm, OTPVerifyForm,
)


# ── Twilio helper ────────────────────────────────────────────
def _send_twilio_sms(to_phone: str, body: str) -> tuple[bool, str]:
    """Send an SMS via Twilio. Returns (success, error_message)."""
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token  = settings.TWILIO_AUTH_TOKEN
    from_phone  = settings.TWILIO_PHONE_NUMBER

    if not all([account_sid, auth_token, from_phone]):
        return False, (
            "Twilio is not configured. "
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER in your .env file."
        )

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(body=body, from_=from_phone, to=to_phone)
        return True, ''
    except Exception as exc:
        return False, str(exc)


# ── Home ────────────────────────────────────────────────────
def home(request):
    donor_count    = DonorProfile.objects.filter(is_available=True).count()
    donation_count = DonationRecord.objects.count()
    request_count  = BloodRequest.objects.filter(status='open').count()
    return render(request, 'home.html', {
        'donor_count': donor_count,
        'donation_count': donation_count,
        'request_count': request_count,
    })


# ── Auth ────────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data['first_name']
            user.last_name  = form.cleaned_data['last_name']
            user.email      = form.cleaned_data['email']
            user.save()

            phone = form.cleaned_data.get('phone', '').strip()
            # Auto-prefix Indian numbers that don't have a country code
            if phone and not phone.startswith('+'):
                phone = '+91' + phone

            DonorProfile.objects.create(
                user=user,
                blood_type=form.cleaned_data['blood_type'],
                phone=phone,
                city=form.cleaned_data.get('city', ''),
                state=form.cleaned_data.get('state', ''),
                has_hiv=form.cleaned_data.get('has_hiv', False),
                has_diabetes=form.cleaned_data.get('has_diabetes', False),
                has_sugar=form.cleaned_data.get('has_sugar', False),
                has_skin_disease=form.cleaned_data.get('has_skin_disease', False),
                covid_vaccinated=form.cleaned_data.get('covid_vaccinated', False),
            )

            # ── Send OTP if a phone was provided ────────────────
            if phone:
                otp = OTPVerification.generate_for(phone)
                ok, err = _send_twilio_sms(
                    phone,
                    f"Your BloodLink OTP is: {otp.code}. Valid for 10 minutes.",
                )
                request.session['otp_user_id'] = user.pk
                request.session['otp_phone']   = phone
                if ok:
                    messages.info(
                        request,
                        f'A 6-digit OTP has been sent to {phone}. Please verify to continue.',
                    )
                else:
                    # SMS failed — show OTP on screen for development
                    try:
                        dev_otp = OTPVerification.objects.filter(phone=phone, is_used=False).order_by('-created_at').first()
                        dev_code = dev_otp.code if dev_otp else '?'
                    except Exception:
                        dev_code = '?'
                    import re
                    clean_err = re.sub(r'\x1b\[[0-9;]*m', '', str(err))
                    # Extract just the core Twilio reason (sentence with "Unable" or first 120 chars)
                    match = re.search(r'Unable to[^.]+\.', clean_err)
                    short_err = match.group(0) if match else clean_err[:120]
                    messages.warning(
                        request,
                        f'⚠️ SMS could not be sent — {short_err} '
                        f'Your OTP is: {dev_code}',
                    )
                return redirect('verify_otp')
            else:
                messages.success(request, f'Welcome to BloodLink, {user.first_name}! 🩸')

            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


def verify_otp_view(request):
    user_id = request.session.get('otp_user_id')
    phone   = request.session.get('otp_phone')

    if not user_id and request.user.is_authenticated:
        user_id = request.user.pk
        try:
            phone = request.user.donor_profile.phone
        except DonorProfile.DoesNotExist:
            messages.error(request, 'No phone number found on your profile.')
            return redirect('profile')

    if not user_id or not phone:
        messages.error(request, 'Session expired. Please register again.')
        return redirect('register')

    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'resend':
            otp = OTPVerification.generate_for(phone)
            ok, err = _send_twilio_sms(
                phone,
                f"Your BloodLink OTP is: {otp.code}. Valid for 10 minutes.",
            )
            if ok:
                messages.success(request, f'A new OTP has been sent to {phone}.')
            else:
                messages.error(request, f'Could not send SMS: {err}')
            return redirect('verify_otp')

        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            entered = form.cleaned_data['code']
            otp_qs  = OTPVerification.objects.filter(
                phone=phone, code=entered, is_used=False
            ).order_by('-created_at')

            otp_obj = otp_qs.first()
            if otp_obj and otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()

                try:
                    profile = user.donor_profile
                    profile.phone_verified = True
                    profile.save()
                except DonorProfile.DoesNotExist:
                    pass

                request.session.pop('otp_user_id', None)
                request.session.pop('otp_phone', None)

                if not request.user.is_authenticated:
                    login(request, user)

                messages.success(
                    request,
                    f'Phone {phone} verified successfully! Welcome, {user.first_name}! 🩸',
                )
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid or expired OTP. Please try again or request a new one.')
    else:
        form = OTPVerifyForm()

    return render(request, 'verify_otp.html', {'form': form, 'phone': phone})


def send_otp_view(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=405)

    phone = request.POST.get('phone', '').strip()
    if not phone:
        return JsonResponse({'ok': False, 'error': 'Phone number is required.'})

    if not phone.startswith('+'):
        phone = '+91' + phone

    otp = OTPVerification.generate_for(phone)
    ok, err = _send_twilio_sms(
        phone,
        f"Your BloodLink OTP is: {otp.code}. Valid for 10 minutes.",
    )
    request.session['otp_phone'] = phone
    if request.user.is_authenticated:
        request.session['otp_user_id'] = request.user.pk
    if ok:
        return JsonResponse({'ok': True, 'sms_sent': True})
    else:
        # SMS failed — return OTP in response so it can be shown on screen
        return JsonResponse({'ok': True, 'sms_sent': False, 'dev_code': otp.code,
                             'message': f'SMS unavailable. Your OTP is: {otp.code}'})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        error = 'Invalid username or password.'
    return render(request, 'registration/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('home')


# ── Dashboard ───────────────────────────────────────────────
@login_required
def dashboard(request):
    try:
        profile = request.user.donor_profile
    except DonorProfile.DoesNotExist:
        profile = DonorProfile.objects.create(user=request.user, blood_type='O+')

    donations    = request.user.donations.all()[:5]
    my_requests  = request.user.blood_requests.all()[:5]
    unread_count = Message.objects.filter(receiver=request.user, is_read=False).count()

    return render(request, 'dashboard.html', {
        'profile': profile,
        'donations': donations,
        'my_requests': my_requests,
        'unread_count': unread_count,
    })


# ── Profile ─────────────────────────────────────────────────
@login_required
def profile_view(request):
    try:
        profile = request.user.donor_profile
    except DonorProfile.DoesNotExist:
        profile = DonorProfile.objects.create(user=request.user, blood_type='O+')

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            user = request.user
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name  = request.POST.get('last_name', user.last_name)
            user.email      = request.POST.get('email', user.email)
            user.save()
            saved = form.save(commit=False)
            if saved.phone != profile.phone:
                saved.phone_verified = False
            saved.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name':  request.user.last_name,
            'email':      request.user.email,
        })
    return render(request, 'profile.html', {'form': form, 'profile': profile})


# ── Search Donors ───────────────────────────────────────────
def search_donors(request):
    form   = DonorSearchForm(request.GET)
    donors = DonorProfile.objects.filter(is_available=True).select_related('user')

    if form.is_valid():
        blood_type = form.cleaned_data.get('blood_type')
        city       = form.cleaned_data.get('city')
        if blood_type:
            donors = donors.filter(blood_type=blood_type)
        if city:
            donors = donors.filter(city__icontains=city)

    return render(request, 'search_donors.html', {'form': form, 'donors': donors})


# ── Donation History + Certificate ─────────────────────────
@login_required
def donation_history(request):
    if request.method == 'POST':
        form = DonationForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.donor = request.user
            record.save()
            try:
                request.user.donor_profile.update_badge()
            except DonorProfile.DoesNotExist:
                pass
            messages.success(request, '🩸 Donation recorded! Download your e-certificate below.')
            return redirect('donation_history')
    else:
        form = DonationForm()

    donations = request.user.donations.all()
    return render(request, 'donation_history.html', {'form': form, 'donations': donations})


@login_required
def download_certificate(request, donation_id):
    donation   = get_object_or_404(DonationRecord, id=donation_id, donor=request.user)
    user       = request.user
    profile    = getattr(user, 'donor_profile', None)
    blood_type = profile.blood_type if profile else 'Unknown'
    full_name  = user.get_full_name() or user.username

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="640" viewBox="0 0 900 640">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#FDF6F0;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#F5EDE6;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="red" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#C0392B;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#e74c3c;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="900" height="640" fill="url(#bg)" rx="20"/>
  <rect width="900" height="12" fill="url(#red)" rx="0"/>
  <circle cx="870" cy="80" r="120" fill="#C0392B" opacity="0.06"/>
  <circle cx="30" cy="560" r="100" fill="#C0392B" opacity="0.06"/>
  <text x="450" y="70" text-anchor="middle" font-family="Georgia,serif" font-size="28" font-weight="bold" fill="#C0392B">🩸 BloodLink</text>
  <text x="450" y="95" text-anchor="middle" font-family="Arial,sans-serif" font-size="13" fill="#7A5C4F" letter-spacing="3">INDIA&apos;S BLOOD DONATION NETWORK</text>
  <line x1="60" y1="115" x2="840" y2="115" stroke="#E8D5C9" stroke-width="1.5"/>
  <text x="450" y="175" text-anchor="middle" font-family="Georgia,serif" font-size="42" font-weight="bold" fill="#1A0A00">Certificate of Appreciation</text>
  <text x="450" y="215" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" fill="#7A5C4F">This is to proudly certify that</text>
  <text x="450" y="278" text-anchor="middle" font-family="Georgia,serif" font-size="52" font-weight="bold" fill="#C0392B">{full_name}</text>
  <text x="450" y="325" text-anchor="middle" font-family="Arial,sans-serif" font-size="17" fill="#1A0A00">has generously donated blood on</text>
  <text x="450" y="360" text-anchor="middle" font-family="Georgia,serif" font-size="26" font-weight="bold" fill="#1A0A00">{donation.date.strftime("%d %B %Y")}</text>
  <text x="450" y="398" text-anchor="middle" font-family="Arial,sans-serif" font-size="17" fill="#1A0A00">at <tspan font-weight="bold">{donation.location}</tspan> · Blood Type: <tspan font-weight="bold" fill="#C0392B">{blood_type}</tspan> · Units: <tspan font-weight="bold">{donation.units}</tspan></text>
  <text x="450" y="445" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" fill="#7A5C4F" font-style="italic">"Your gift of blood is a gift of life. You are a true hero."</text>
  <line x1="150" y1="475" x2="750" y2="475" stroke="#E8D5C9" stroke-width="1"/>
  <text x="450" y="520" text-anchor="middle" font-size="36">🩸</text>
  <text x="450" y="570" text-anchor="middle" font-family="Arial,sans-serif" font-size="13" fill="#B08070">Certificate ID: BL-{donation.id:06d} | Issued by BloodLink | www.bloodlink.in</text>
  <text x="450" y="598" text-anchor="middle" font-family="Arial,sans-serif" font-size="12" fill="#B08070">Every drop counts · Saving lives across India</text>
  <rect y="628" width="900" height="12" fill="url(#red)" rx="0"/>
</svg>'''

    response = HttpResponse(svg, content_type='image/svg+xml')
    response['Content-Disposition'] = f'attachment; filename="BloodLink_Certificate_{donation.id}.svg"'
    return response


# ── Blood Requests ──────────────────────────────────────────
def request_blood(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')
        form = BloodRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.requester = request.user
            req.save()
            messages.success(request, 'Blood request submitted! Donors will be notified.')
            return redirect('request_blood')
    else:
        form = BloodRequestForm()

    open_requests = BloodRequest.objects.filter(status='open').order_by('-created_at')
    return render(request, 'request_blood.html', {'form': form, 'open_requests': open_requests})


# ── Messages ────────────────────────────────────────────────
@login_required
def inbox(request):
    conversations = User.objects.filter(
        Q(sent_messages__receiver=request.user) |
        Q(received_messages__sender=request.user)
    ).distinct().exclude(id=request.user.id)
    return render(request, 'inbox.html', {'conversations': conversations})


@login_required
def conversation(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    msgs = Message.objects.filter(
        Q(sender=request.user, receiver=other_user) |
        Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            Message.objects.create(sender=request.user, receiver=other_user, content=content)
            return redirect('conversation', user_id=user_id)

    return render(request, 'conversation.html', {'other_user': other_user, 'messages': msgs})


# ── Gallery ─────────────────────────────────────────────────
def gallery(request):
    photos      = GalleryPhoto.objects.all()
    featured    = photos.filter(is_featured=True)[:6]
    all_photos  = photos[:50]
    upload_form = None

    if request.user.is_authenticated and request.user.is_staff:
        if request.method == 'POST':
            upload_form = GalleryUploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                photo = upload_form.save(commit=False)
                photo.uploaded_by = request.user
                photo.save()
                messages.success(request, 'Photo uploaded to gallery!')
                return redirect('gallery')
        else:
            upload_form = GalleryUploadForm()

    return render(request, 'gallery.html', {
        'photos': all_photos,
        'featured': featured,
        'upload_form': upload_form,
    })


# ── AI Chat (Gemini) ─────────────────────────────────────────
SYSTEM_PROMPT = """You are BloodBot 🩸, a friendly and knowledgeable AI assistant for BloodLink — a blood donation platform in India.
You help users with:
- Blood donation eligibility criteria
- Finding blood donors
- Understanding blood types and compatibility (A, B, AB, O with +/-)
- Donation process and what to expect
- Post-donation care and diet
- Emergency blood requests
- BloodLink platform features
Keep answers concise (2-4 sentences), warm, and supportive. Always encourage donation when appropriate.
Reply in the same language the user uses (English or Tamil or Hindi).
Start your first reply with a friendly greeting."""


@csrf_exempt
@require_POST
def ai_chat(request):
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return JsonResponse({'reply': '⚠️ BloodBot is not configured. Please set GEMINI_API_KEY in your .env file.'})

    try:
        data    = json.loads(request.body)
        message = data.get('message', '').strip()
        history = data.get('history', [])

        if not message:
            return JsonResponse({'reply': 'Please type a message!'})

        contents = history + [{'role': 'user', 'parts': [{'text': message}]}]
        payload  = json.dumps({
            'system_instruction': {'parts': [{'text': SYSTEM_PROMPT}]},
            'contents': contents,
            'generationConfig': {'maxOutputTokens': 350, 'temperature': 0.7}
        }).encode('utf-8')

        # Try multiple models for best compatibility
        models_to_try = ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-pro']
        result = None
        last_error = None
        for model_name in models_to_try:
            try:
                url = f'https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}'
                req2 = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req2, timeout=15) as resp:
                    result = json.loads(resp.read().decode('utf-8'))
                break
            except urllib.error.HTTPError as e:
                last_error = f'HTTP {e.code}: {e.read().decode()}'
                print(f'BloodBot model {model_name} failed: {last_error}')
                continue
        if result is None:
            return JsonResponse({'reply': f'⚠️ Gemini error: {last_error}'})
        url = ''  # already used above
        reply = result['candidates'][0]['content']['parts'][0]['text']
        return JsonResponse({'reply': reply})

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f'Gemini HTTP error {e.code}: {body}')
        return JsonResponse({'reply': f'⚠️ Gemini API error {e.code}: {body}'})

    except urllib.error.URLError as e:
        print(f'BloodBot URL error: {e.reason}')
        return JsonResponse({'reply': f'⚠️ Network error: {e.reason}'})

    except KeyError:
        print(f'BloodBot: unexpected response format: {result}')
        return JsonResponse({'reply': f'⚠️ Unexpected response from Gemini: {result}'})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'reply': f'⚠️ Error: {str(e)}'})

# ── OTP Login (phone-based login) ───────────────────────────
@csrf_exempt
@require_POST
def login_otp_view(request):
    """Verify OTP submitted from the login page and log the user in."""
    phone = request.POST.get('phone', '').strip()
    code  = request.POST.get('code', '').strip()

    if not phone or not code:
        return JsonResponse({'ok': False, 'error': 'Phone and OTP are required.'})

    if not phone.startswith('+'):
        phone = '+91' + phone

    # Find a DonorProfile with this phone
    try:
        profile = DonorProfile.objects.select_related('user').get(phone=phone)
    except DonorProfile.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'No account found with this phone number.'})

    # Validate OTP
    otp_obj = OTPVerification.objects.filter(
        phone=phone, code=code, is_used=False
    ).order_by('-created_at').first()

    if not otp_obj or not otp_obj.is_valid():
        return JsonResponse({'ok': False, 'error': 'Invalid or expired OTP. Please try again.'})

    # Mark used, log user in
    otp_obj.is_used = True
    otp_obj.save()

    profile.phone_verified = True
    profile.save()

    login(request, profile.user)
    return JsonResponse({'ok': True, 'redirect': '/dashboard/'})
