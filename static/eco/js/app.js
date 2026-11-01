(function () {
  'use strict';

  const root = document.documentElement;
  const text = window.BookBazarText || {};

  function csrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : '';
  }

  /* ---------- Toasts ---------- */
  const ICONS = {
    success: 'fa-circle-check',
    error: 'fa-circle-exclamation',
    warning: 'fa-triangle-exclamation',
    info: 'fa-circle-info',
  };

  function toastStack() {
    let stack = document.querySelector('.toast-stack');
    if (!stack) {
      stack = document.createElement('div');
      stack.className = 'toast-stack';
      stack.setAttribute('aria-live', 'polite');
      document.body.appendChild(stack);
    }
    return stack;
  }

  function toast(message, type = 'info', { html = false, timeout = 4000 } = {}) {
    if (type === 'danger') type = 'error';
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.innerHTML = `<i class="fa-solid ${ICONS[type] || ICONS.info}"></i><div class="toast-body"></div>
      <button class="toast-close" aria-label="${text.dismiss || 'Dismiss'}"><i class="fa-solid fa-xmark"></i></button>`;
    const body = el.querySelector('.toast-body');
    if (html) body.innerHTML = message; else body.textContent = message;

    const close = () => {
      el.classList.add('is-leaving');
      setTimeout(() => el.remove(), 250);
    };
    el.querySelector('.toast-close').addEventListener('click', close);
    toastStack().appendChild(el);
    if (timeout) setTimeout(close, timeout);
  }

  /* ---------- API helper ---------- */
  async function api(url, { method = 'POST', body } = {}) {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: method === 'GET' ? undefined : JSON.stringify(body || {}),
      credentials: 'same-origin',
    });

    let data = {};
    try { data = await response.json(); } catch (e) { /* non-JSON response */ }

    if (response.status === 401 && data.login_url) {
      window.location.href = data.login_url;
      return new Promise(() => {});
    }
    if (!response.ok && data.success === undefined) {
      throw new Error(data.message || data.error || text.genericError);
    }
    return data;
  }

  function setLoading(button, loading) {
    if (!button) return;
    button.classList.toggle('is-loading', loading);
    button.disabled = loading;
  }

  function setCartCount(count) {
    document.querySelectorAll('[data-cart-count]').forEach((badge) => {
      badge.textContent = count;
      badge.classList.toggle('is-empty', !count);
      badge.classList.add('bump');
      setTimeout(() => badge.classList.remove('bump'), 250);
    });
  }

  /* ---------- Add to cart ---------- */
  async function addToCart(button) {
    const qtyInput = button.dataset.qtyInput && document.querySelector(button.dataset.qtyInput);
    const quantity = qtyInput ? parseInt(qtyInput.value, 10) || 1 : 1;
    setLoading(button, true);
    try {
      const data = await api(button.dataset.addToCart, { body: { quantity } });
      if (data.success) {
        setCartCount(data.total_items);
        const cartUrl = document.body.dataset.cartUrl;
        toast(`${escapeHtml(data.message)} <a href="${cartUrl}">${escapeHtml(text.viewCart)}</a>`, 'success', { html: true });
      } else {
        toast(data.message || text.cartError, 'warning');
      }
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      setLoading(button, false);
    }
  }

  /* ---------- Wishlist ---------- */
  async function toggleWishlist(button) {
    const active = button.classList.contains('is-active');
    const url = active ? button.dataset.removeUrl : button.dataset.addUrl;
    button.disabled = true;
    try {
      const data = await api(url, { method: active ? 'POST' : 'GET' });
      if (data.success) {
        setWishlistState(button, !active);
        toast(active ? text.removedFromWishlist : text.addedToWishlist, 'success');
        if (active && button.dataset.removeCard) {
          const card = button.closest(button.dataset.removeCard);
          if (card) {
            card.style.transition = 'opacity .3s, transform .3s';
            card.style.opacity = '0';
            card.style.transform = 'scale(.96)';
            setTimeout(() => {
              card.remove();
              document.dispatchEvent(new CustomEvent('wishlist:removed'));
            }, 300);
          }
        }
      } else {
        toast(data.message || text.wishlistError, 'warning');
      }
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      button.disabled = false;
    }
  }

  function setWishlistState(button, active) {
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-pressed', active ? 'true' : 'false');
    const icon = button.querySelector('i');
    if (icon) icon.className = `${active ? 'fa-solid' : 'fa-regular'} fa-heart`;
    const label = button.querySelector('[data-label]');
    if (label) label.textContent = active ? text.saved : text.save;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  /* ---------- Event delegation ---------- */
  document.addEventListener('click', (event) => {
    const addButton = event.target.closest('[data-add-to-cart]');
    if (addButton) {
      event.preventDefault();
      addToCart(addButton);
      return;
    }

    const wishButton = event.target.closest('[data-wishlist]');
    if (wishButton) {
      event.preventDefault();
      toggleWishlist(wishButton);
      return;
    }

    const stepper = event.target.closest('[data-qty-step]');
    if (stepper) {
      const input = stepper.closest('.qty').querySelector('input');
      const max = parseInt(input.max, 10) || Infinity;
      const next = (parseInt(input.value, 10) || 1) + parseInt(stepper.dataset.qtyStep, 10);
      input.value = Math.min(Math.max(next, 1), max);
      return;
    }

    if (event.target.closest('[data-theme-toggle]')) {
      const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      root.dataset.theme = next;
      try { localStorage.setItem('theme', next); } catch (e) { /* storage unavailable */ }
      return;
    }

    if (event.target.closest('[data-nav-toggle]')) {
      const nav = document.querySelector('.mobile-nav');
      const open = nav.classList.toggle('is-open');
      document.body.style.overflow = open ? 'hidden' : '';
      const icon = document.querySelector('[data-nav-toggle] i');
      if (icon) icon.className = `fa-solid ${open ? 'fa-xmark' : 'fa-bars'}`;
      return;
    }

    // Close open dropdown menus when clicking elsewhere
    document.querySelectorAll('details.menu[open]').forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute('open');
    });
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      document.querySelectorAll('details.menu[open]').forEach((menu) => menu.removeAttribute('open'));
    }
  });

  /* ---------- Header shadow on scroll ---------- */
  const header = document.querySelector('.site-header');
  const onScroll = () => header && header.classList.toggle('is-scrolled', window.scrollY > 8);
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- Reveal on scroll ---------- */
  const revealItems = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -40px 0px' });
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add('is-visible'));
  }

  /* ---------- Django messages as toasts ---------- */
  document.querySelectorAll('[data-message]').forEach((message) => {
    toast(message.textContent.trim(), message.dataset.message || 'info', { timeout: 6000 });
  });

  window.BookBazar = { api, toast, setLoading, setCartCount, csrfToken };
})();
