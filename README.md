# 🩸 BloodLink v2 — Complete Upgrade

## Quick Start

```bash
cd bloodlink

# 1. Create virtual environment


source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Gemini API key
cp .env.example .env
# Edit .env: set GEMINI_API_KEY=AIzaSy...

# 4. Setup database
python manage.py migrate

# 5. Create admin (for gallery uploads)
python manage.py createsuperuser

# 6. Run
python manage.py runserver
```

Visit: http://127.0.0.1:8000

---

## What's New in v2

| Feature | Details |
|---|---|
| 🤖 BloodBot AI Fixed | Now works correctly via backend Gemini route |
| 💬 Quick Reply Chips | Tap suggestion buttons to ask common questions |
| 📸 Donation Photo Upload | Upload a photo with each donation record |
| 🏆 E-Certificate | Download beautiful SVG certificate for each donation |
| 🖼️ Events Gallery | Photo gallery page with lightbox viewer |
| 🎨 Particle Background | Animated interactive particles on hero section |
| 👤 No Fake Donor Names | Hero cards now show blood type info, not fake names |
| 🔢 Animated Counters | Stats count up on page load |

---

## Gallery Upload (Admin Only)
1. Go to /admin/ and log in with superuser
2. Or visit /gallery/ while logged in as staff
3. Upload event photos with title, date, description

---

## Free Gemini API Key
1. https://aistudio.google.com
2. Sign in with Google (no credit card)
3. Get API Key → Create API Key
4. Add to .env: GEMINI_API_KEY=AIzaSy...
