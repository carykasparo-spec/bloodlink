/* ============================================================
   BloodLink v2 — main.js
   • Theme toggle (full CSS variable coverage)
   • Particle background
   • Scroll reveal animations
   • BloodBot — tries backend, falls back to direct Gemini
   • Quick-reply chips
   • Ripple effects
   • Navbar scroll shadow
   ============================================================ */

/* ── Theme (apply immediately before render) ─────────────── */
(function () {
  var t = localStorage.getItem('bl-theme') || 'light';
  document.documentElement.setAttribute('data-theme', t);
})();

function toggleTheme() {
  const root = document.documentElement;
  const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  localStorage.setItem('bl-theme', next);
  updateThemeBtn(next);
}

function updateThemeBtn(theme) {
  const btn = document.getElementById('theme-toggle');
  if (!btn) return;
  btn.innerHTML = theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';
}

/* ── Particle Background ──────────────────────────────────── */
function initParticles() {
  const canvas = document.getElementById('particle-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width  = canvas.parentElement.offsetWidth  || window.innerWidth;
    canvas.height = canvas.parentElement.offsetHeight || 500;
  }
  resize();
  window.addEventListener('resize', () => { resize(); });

  const particles = Array.from({ length: 50 }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    r: Math.random() * 3.5 + 1.2,
    dx: (Math.random() - 0.5) * 0.55,
    dy: (Math.random() - 0.5) * 0.55,
    op: Math.random() * 0.38 + 0.08,
  }));

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    const col  = dark ? '240,100,80' : '192,57,43';

    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${col},${p.op})`;
      ctx.fill();
      p.x += p.dx; p.y += p.dy;
      if (p.x < 0 || p.x > canvas.width)  p.dx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
    });

    particles.forEach((a, i) => {
      for (let j = i + 1; j < particles.length; j++) {
        const b = particles[j];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 110) {
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = `rgba(${col},${0.07 * (1 - d / 110)})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    });
    requestAnimationFrame(draw);
  }
  draw();
}

/* ── Scroll Reveal ────────────────────────────────────────── */
function initScrollReveal() {
  const els = document.querySelectorAll('.reveal');
  if (!els.length) return;
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  els.forEach(el => io.observe(el));
}

/* ── Navbar scroll shadow ─────────────────────────────────── */
function initNavbarScroll() {
  const nav = document.querySelector('.navbar');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 20);
  }, { passive: true });
}

/* ── Ripple effect ────────────────────────────────────────── */
function initRipple() {
  document.querySelectorAll('.btn-blood, .btn-outline-blood').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const r = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      r.style.cssText = `position:absolute;width:${size}px;height:${size}px;
        left:${e.clientX - rect.left - size/2}px;top:${e.clientY - rect.top - size/2}px;
        border-radius:50%;background:rgba(255,255,255,0.3);transform:scale(0);
        animation:ripple 0.5s linear;pointer-events:none;`;
      this.style.position = 'relative';
      this.style.overflow = 'hidden';
      this.appendChild(r);
      setTimeout(() => r.remove(), 600);
    });
  });
}

/* ── BloodBot ─────────────────────────────────────────────── */
let chatHistory = [];

const SYSTEM_PROMPT = `You are BloodBot 🩸, a friendly AI assistant for BloodLink — India's blood donation platform.
Help users with: donation eligibility, blood type compatibility, donation process, post-donation care, finding donors, emergency requests.
Keep replies concise (2-4 sentences), warm, supportive. Encourage donation. Reply in the user's language (English/Tamil/Hindi).`;

const QUICK_REPLIES = [
  'Am I eligible to donate?',
  'Blood type compatibility?',
  'What to eat after donating?',
  'How often can I donate?',
];

async function callGeminiDirect(message) {
  const key = (window.GEMINI_API_KEY || '').trim();
  if (!key) return null;

  const body = {
    system_instruction: { parts: [{ text: SYSTEM_PROMPT }] },
    contents: chatHistory.concat([{ role: 'user', parts: [{ text: message }] }]),
    generationConfig: { maxOutputTokens: 300, temperature: 0.7 }
  };

  // Try gemini-1.5-flash first (most stable), fallback to 2.0-flash
  const models = ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-pro'];
  for (const model of models) {
    try {
      const res = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
      );
      if (!res.ok) continue;
      const data = await res.json();
      const text = data.candidates?.[0]?.content?.parts?.[0]?.text;
      if (text) return text;
    } catch { continue; }
  }
  return null;
}

async function callGeminiBackend(message) {
  try {
    const res = await fetch('/api/chat/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
      body: JSON.stringify({ message, history: chatHistory })
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (data.reply && !data.reply.startsWith('⚠️')) return data.reply;
    return null;
  } catch { return null; }
}

async function sendBotMessage(text) {
  const input = document.getElementById('bloodbot-input');
  if (input) input.value = '';
  removeQR();
  appendMsg(text, 'user');
  const typing = showTyping();

  let reply = await callGeminiBackend(text);
  if (!reply) reply = await callGeminiDirect(text);
  if (!reply) reply = '⚠️ BloodBot is offline. Check your internet connection or try again shortly.';

  chatHistory.push(
    { role: 'user',  parts: [{ text }] },
    { role: 'model', parts: [{ text: reply }] }
  );
  typing?.remove();
  appendMsg(reply, 'bot');
}

function removeQR() { const el = document.getElementById('quick-replies'); if (el) el.remove(); }

function renderQuickReplies() {
  const box = document.getElementById('bloodbot-messages');
  if (!box || document.getElementById('quick-replies')) return;
  const wrap = document.createElement('div');
  wrap.id = 'quick-replies';
  QUICK_REPLIES.forEach(text => {
    const chip = document.createElement('button');
    chip.textContent = text;
    chip.onclick = () => sendBotMessage(text);
    wrap.appendChild(chip);
  });
  box.appendChild(wrap);
  box.scrollTop = box.scrollHeight;
}

function appendMsg(text, sender) {
  const box = document.getElementById('bloodbot-messages');
  if (!box) return;
  const div = document.createElement('div');
  div.className = `msg msg-${sender}`;
  div.innerHTML = text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>');
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function showTyping() {
  const box = document.getElementById('bloodbot-messages');
  if (!box) return null;
  const div = document.createElement('div');
  div.className = 'msg msg-bot typing-dots';
  div.innerHTML = '<span></span><span></span><span></span>';
  div.id = 'typing-indicator';
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

async function handleSend() {
  const input = document.getElementById('bloodbot-input');
  const text = input?.value?.trim();
  if (!text) return;
  await sendBotMessage(text);
}


/* ── CSRF ─────────────────────────────────────────────────── */
function getCookie(name) {
  const v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
  return v ? v.pop() : '';
}

/* ── Animated counter ─────────────────────────────────────── */
function initCounters() {
  document.querySelectorAll('[data-target]').forEach(el => {
    const target = parseInt(el.dataset.target) || 0;
    if (!target) { el.textContent = '0+'; return; }
    let cur = 0;
    const step = Math.max(1, Math.ceil(target / 55));
    const t = setInterval(() => {
      cur = Math.min(cur + step, target);
      el.textContent = cur.toLocaleString() + '+';
      if (cur >= target) clearInterval(t);
    }, 22);
  });
}

/* ── Init ─────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {

  // Theme
  const themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', toggleTheme);
    updateThemeBtn(document.documentElement.getAttribute('data-theme'));
  }

  // All features
  initParticles();
  initScrollReveal();
  initNavbarScroll();
  initRipple();
  initCounters();

  // BloodBot
  const fab   = document.getElementById('bloodbot-btn');
  const win   = document.getElementById('bloodbot-window');
  const close = document.getElementById('bloodbot-close');

  if (fab && win) {
    fab.addEventListener('click', () => {
      const opening = !win.classList.contains('open');
      win.classList.toggle('open');
      if (opening && chatHistory.length === 0) {
        setTimeout(renderQuickReplies, 200);
      }
    });
  }
  if (close && win) close.addEventListener('click', () => win.classList.remove('open'));

  const sendBtn = document.getElementById('bloodbot-send');
  if (sendBtn) sendBtn.addEventListener('click', handleSend);

  const inp = document.getElementById('bloodbot-input');
  if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } });

  // Gallery lightbox
  document.querySelectorAll('.gallery-img').forEach(img => {
    img.addEventListener('click', () => {
      const lb = document.getElementById('lightbox');
      const lbImg = document.getElementById('lightbox-img');
      const lbCap = document.getElementById('lightbox-caption');
      if (lb && lbImg) {
        lbImg.src = img.src;
        if (lbCap) lbCap.textContent = img.dataset.caption || '';
        lb.style.display = 'flex';
      }
    });
  });
  const lb = document.getElementById('lightbox');
  if (lb) lb.addEventListener('click', () => { lb.style.display = 'none'; });
});

// Also add style for ripple keyframe
const s = document.createElement('style');
s.textContent = '@keyframes ripple { to { transform:scale(3); opacity:0; } }';
document.head.appendChild(s);
