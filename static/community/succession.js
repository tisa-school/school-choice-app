/* Visible by default, with entrances reserved for a few editorial groups. */
(() => {
  const seen = new Set();
  const running = new Map();
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  let observer;
  let currentVisit;
  const reduced = () => {
    let local = false;
    try { local = localStorage.getItem('reduce-motion') === 'true'; } catch (_) {}
    return preference.matches || local || document.documentElement.classList.contains('reduced-motion');
  };
  function clear() {
    observer?.disconnect();
    running.forEach(animation => animation.cancel());
    running.clear();
  }
  function scan(root = document, key = location.pathname) {
    clear();
    // A new route visit may reveal again; state-only renders never call scan.
    if (currentVisit !== key) { seen.clear(); currentVisit = key; }
    if (reduced() || !('IntersectionObserver' in window)) return;
    const scope = root === document ? document.querySelector('main') : root;
    if (!scope) return;
    const candidates = [...scope.querySelectorAll('h1, [data-reveal], [data-succession]')].filter(element =>
      !element.closest('form, dialog, nav, [role="status"], [role="alert"], [aria-live], [data-succession-skip]') &&
      !element.querySelector('form, button, input, select, textarea, a, [role="button"]')
    );
    const nodes = candidates.filter(element => !candidates.some(parent => parent !== element && parent.contains(element))).slice(0, 4);
    const idFor = element => key + ':' + (element.dataset.reveal || (element.tagName === 'H1' ? 'title' : 'editorial-' + nodes.indexOf(element)));
    try {
      observer = new IntersectionObserver(entries => {
        let stagger = 0;
        entries.forEach(({ target, isIntersecting }) => {
          if (!isIntersecting) return;
          observer.unobserve(target);
          const id = idFor(target);
          if (seen.has(id)) return;
          seen.add(id);
          const bounds = target.getBoundingClientRect();
          // Fast scrolls and busy frames skip effects; content never waits in a hidden state.
          if (bounds.bottom <= 0 || bounds.top >= innerHeight || reduced() || document.hidden || running.size >= 2 || target.contains(document.activeElement) || !target.animate) return;
          try {
            const animation = target.animate([
              { transform: 'scale(0.94)', filter: 'blur(4px)', opacity: 0 },
              { transform: 'scale(1)', filter: 'blur(0px)', opacity: 1 }
            ], { duration: 580, delay: Math.min(stagger++ * 100, 100), easing: 'cubic-bezier(0.22, 1, 0.36, 1)', fill: 'backwards' });
            running.set(target, animation);
            animation.onfinish = animation.oncancel = () => running.delete(target);
          } catch (_) { /* Animation support is optional. */ }
        });
      }, { threshold: 0 });
      nodes.filter(element => !seen.has(idFor(element))).forEach(element => observer.observe(element));
    } catch (_) { clear(); }
  }
  preference.addEventListener('change', () => { if (reduced()) clear(); });
  new MutationObserver(() => { if (reduced()) clear(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  document.addEventListener('focusin', event => running.forEach((animation, element) => { if (element.contains(event.target)) animation.cancel(); }));
  document.addEventListener('visibilitychange', () => { if (document.hidden) clear(); });
  window.addEventListener('pagehide', clear);
  window.SuccessionReveal = { scan, clear };
  document.addEventListener('DOMContentLoaded', () => {
    // The interactive demo calls scan after rendering; never animate its loading placeholder.
    if (!document.getElementById('demo-shell')) scan();
  }, { once: true });
})();
