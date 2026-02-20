// ══════════════════════════════════════════════
//  THEME TOGGLE
// ══════════════════════════════════════════════
const themeBtn  = document.getElementById('theme-btn');
const sunIcon   = themeBtn.querySelector('.sun-icon');
const moonIcon  = themeBtn.querySelector('.moon-icon');

function applyTheme(theme) {
  if (theme === 'light') {
    document.body.classList.add('light');
    sunIcon.classList.remove('hidden');
    moonIcon.classList.add('hidden');
  } else {
    document.body.classList.remove('light');
    sunIcon.classList.add('hidden');
    moonIcon.classList.remove('hidden');
  }
}

applyTheme(localStorage.getItem('theme') || 'dark');

themeBtn.addEventListener('click', () => {
  const next = document.body.classList.contains('light') ? 'dark' : 'light';
  localStorage.setItem('theme', next);
  applyTheme(next);
});

// ══════════════════════════════════════════════
//  NAVBAR: scroll shadow + active link
// ══════════════════════════════════════════════
const navbar  = document.getElementById('navbar');
const navLinks = document.querySelectorAll('.nav-links a');
const sections = document.querySelectorAll('section[id]');

window.addEventListener('scroll', () => {
  // Shadow on scroll
  navbar.classList.toggle('scrolled', window.scrollY > 30);

  // Active link highlight
  let current = '';
  sections.forEach(sec => {
    if (window.scrollY >= sec.offsetTop - 120) current = sec.id;
  });
  navLinks.forEach(link => {
    link.classList.toggle('active', link.getAttribute('href') === '#' + current);
  });
}, { passive: true });

// ══════════════════════════════════════════════
//  MOBILE MENU
// ══════════════════════════════════════════════
const mobileBtn  = document.getElementById('mobile-btn');
const mobileMenu = document.getElementById('mobile-menu');

mobileBtn.addEventListener('click', () => {
  const open = mobileMenu.style.display === 'flex';
  mobileMenu.style.display = open ? 'none' : 'flex';
});

mobileMenu.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => { mobileMenu.style.display = 'none'; });
});

// ══════════════════════════════════════════════
//  SCROLL REVEAL (sections + .reveal elements)
// ══════════════════════════════════════════════
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;

    // Reveal animation
    entry.target.classList.add('visible');

    // Animate skill bars inside this element
    entry.target.querySelectorAll('.skill-fill').forEach(bar => {
      const target = bar.dataset.width + '%';
      // Small delay so the reveal transition starts first
      setTimeout(() => { bar.style.width = target; }, 200);
    });

    revealObserver.unobserve(entry.target);
  });
}, { threshold: 0.12 });

document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

// ══════════════════════════════════════════════
//  CONTACT FORM
// ══════════════════════════════════════════════
const form      = document.getElementById('contact-form');
const submitBtn = document.getElementById('submit-btn');
const btnLabel  = document.getElementById('btn-label');
const formMsg   = document.getElementById('form-msg');

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  submitBtn.disabled = true;
  btnLabel.textContent = 'Sending…';
  formMsg.className = 'form-msg hidden';

  const payload = {
    name:    form.name.value.trim(),
    email:   form.email.value.trim(),
    subject: form.subject.value.trim(),
    message: form.message.value.trim(),
  };

  try {
    const res    = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await res.json();

    if (res.ok) {
      formMsg.textContent = '✓ Message sent! I\'ll get back to you soon.';
      formMsg.className = 'form-msg success';
      form.reset();
    } else {
      throw new Error(result.detail || 'Failed to send.');
    }
  } catch (err) {
    formMsg.textContent = '✗ ' + (err.message || 'Something went wrong. Try emailing directly.');
    formMsg.className = 'form-msg error';
  } finally {
    submitBtn.disabled = false;
    btnLabel.textContent = 'Send Message';
  }
});
