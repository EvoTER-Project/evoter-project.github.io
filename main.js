// Copy-to-clipboard for the BibTeX block.
document.querySelectorAll('button.copy').forEach((btn) => {
  btn.addEventListener('click', async () => {
    const target = document.querySelector(btn.dataset.copy);
    if (!target) return;
    try {
      await navigator.clipboard.writeText(target.innerText);
      btn.textContent = 'Copied';
    } catch (e) {
      const range = document.createRange();
      range.selectNodeContents(target);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      btn.textContent = 'Press Ctrl/Cmd+C';
    }
    setTimeout(() => { btn.textContent = 'Copy'; }, 1800);
  });
});

// Videos: show a placeholder until the clip is added to assets/video/.
document.querySelectorAll('.video-card video').forEach((video) => {
  const source = video.querySelector('source');
  const showPlaceholder = () => {
    if (video.dataset.missing) return;
    video.dataset.missing = '1';
    const box = document.createElement('div');
    box.className = 'video-missing';
    box.textContent = 'Video coming soon (' + source.getAttribute('src').split('/').pop() + ')';
    video.replaceWith(box);
  };
  if (source) source.addEventListener('error', showPlaceholder);
  video.addEventListener('error', showPlaceholder);
});

// Apply the configured playback rate before autoplay begins.
document.querySelectorAll('video[data-playback-rate]').forEach((video) => {
  video.defaultPlaybackRate = Number(video.dataset.playbackRate);
  video.playbackRate = video.defaultPlaybackRate;
});

// Autoplay muted clips only while they are on screen; honour reduced-motion settings.
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const autoVideos = document.querySelectorAll('video[data-autoplay]');
if (reduceMotion || !('IntersectionObserver' in window)) {
  autoVideos.forEach((v) => { v.controls = true; });
} else {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      const v = e.target;
      if (e.isIntersecting) { v.play().catch(() => { v.controls = true; }); }
      else { v.pause(); }
    });
  }, { threshold: 0.25 });
  autoVideos.forEach((v) => io.observe(v));
}

// Each case-study tab list operates independently (all cases stay visible without JS).
document.querySelectorAll('.case-nav[role="tablist"]').forEach((nav) => {
  const tabs = [...nav.querySelectorAll('[role="tab"]')];
  if (!tabs.length) return;
  const select = (tab, focus) => {
    tabs.forEach((t) => {
      const on = t === tab;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      const panel = document.getElementById(t.getAttribute('aria-controls'));
      panel.hidden = !on;
      if (!on) panel.querySelectorAll('video').forEach((v) => v.pause());
    });
    if (focus) tab.focus();
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => select(tab, false));
    tab.addEventListener('keydown', (e) => {
      const k = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
      if (k) { e.preventDefault(); select(tabs[(i + k + tabs.length) % tabs.length], true); }
      else if (e.key === 'Home') { e.preventDefault(); select(tabs[0], true); }
      else if (e.key === 'End') { e.preventDefault(); select(tabs[tabs.length - 1], true); }
    });
  });
  select(tabs[0], false);
});
