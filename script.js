// AITerm product site — script.js

// ── Fetch latest release from GitHub API ──
(async () => {
  const RELEASES_API = 'https://api.github.com/repos/jamesju9999/AITERM/releases/latest';
  const downloadBtns = document.querySelectorAll('.download-btn');

  try {
    const res = await fetch(RELEASES_API, {
      headers: { Accept: 'application/vnd.github+json' }
    });
    if (!res.ok) return;

    const release = await res.json();
    const releaseUrl = release.html_url;       // e.g. .../releases/tag/v0.1.51
    const tagName    = release.tag_name;        // e.g. v0.1.51

    downloadBtns.forEach(btn => {
      btn.href = releaseUrl;
      const versionSpan = btn.querySelector('.release-version');
      if (versionSpan) versionSpan.textContent = tagName;
    });

    // Also update the install step link
    document.querySelectorAll('.release-link').forEach(a => {
      a.href = releaseUrl;
    });
  } catch {
    // Network error: keep the static fallback href
  }
})();

// ── Tab switching ──
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
  });
});

// ── Linux arch selector ──
document.querySelectorAll('.linux-arch-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const arch = btn.dataset.arch;
    document.querySelectorAll('.linux-arch-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.linux-arch-content').forEach(c => c.style.display = 'none');
    btn.classList.add('active');
    document.getElementById('linux-' + arch).style.display = 'block';
  });
});

// ── Copy buttons ──
document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const text = btn.dataset.code;
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = '已複製！';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.textContent = orig;
        btn.classList.remove('copied');
      }, 2000);
    });
  });
});

// ── Mobile nav toggle ──
const toggle = document.querySelector('.nav-toggle');
const navLinks = document.querySelector('.nav-links');
toggle.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});

// Close mobile nav on link click
navLinks.querySelectorAll('a').forEach(a => {
  a.addEventListener('click', () => navLinks.classList.remove('open'));
});

// ── Navbar shadow on scroll ──
const nav = document.querySelector('.nav');
window.addEventListener('scroll', () => {
  nav.style.boxShadow = window.scrollY > 10
    ? '0 2px 20px rgba(0,0,0,0.5)'
    : 'none';
}, { passive: true });

// ── Fade-in on scroll ──
const observer = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.feature-card, .arch-layer, .install-steps li').forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(16px)';
  el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
  observer.observe(el);
});
