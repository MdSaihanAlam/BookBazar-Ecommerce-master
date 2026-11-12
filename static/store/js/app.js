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
        if (cartDrawer) {
          openCartDrawer();
        } else {
          const cartUrl = document.body.dataset.cartUrl;
          toast(`${escapeHtml(data.message)} <a href="${cartUrl}">${escapeHtml(text.viewCart)}</a>`, 'success', { html: true });
        }
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

  /* Convert a US dollar amount to the visitor's currency, matching store/currency.py's format_money. */
  function formatMoney(amountUsd) {
    const currency = window.BookBazarCurrency || { symbol: '$', rate: 1, decimals: 2 };
    const value = Number(amountUsd) * currency.rate;
    return currency.symbol + value.toLocaleString('en-US', {
      minimumFractionDigits: currency.decimals,
      maximumFractionDigits: currency.decimals,
    });
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  /* ---------- Modal dialogs ---------- */
  function openDialog(dialog) {
    if (dialog.open) return;
    dialog.showModal();
    document.body.classList.add('has-dialog');
  }

  function closeDialog(dialog) {
    if (!dialog.open) return;
    dialog.classList.add('is-closing');
    setTimeout(() => {
      dialog.classList.remove('is-closing');
      dialog.close();
    }, 180);
  }

  document.querySelectorAll('dialog').forEach((dialog) => {
    dialog.addEventListener('close', () => document.body.classList.remove('has-dialog'));
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      closeDialog(dialog);
    });
    // A click on the backdrop lands on the dialog element itself
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) closeDialog(dialog);
    });
  });

  /* ---------- Search palette ---------- */
  const palette = document.getElementById('searchPalette');
  const paletteInput = palette && palette.querySelector('input');
  const paletteResults = palette && palette.querySelector('.palette-results');
  let paletteRequest = 0;
  let paletteTimer = null;

  function openPalette() {
    if (!palette) return;
    closeMobileNav();
    openDialog(palette);
    paletteInput.select();
    if (!paletteResults.childElementCount) loadSuggestions('');
  }

  async function loadSuggestions(query) {
    const request = ++paletteRequest;
    const url = `${palette.dataset.suggestUrl}?q=${encodeURIComponent(query)}`;
    try {
      const data = await api(url, { method: 'GET' });
      if (request === paletteRequest) renderSuggestions(data, query);
    } catch (error) {
      if (request === paletteRequest) paletteResults.innerHTML = `<p class="palette-empty">${escapeHtml(error.message)}</p>`;
    }
  }

  function renderSuggestions(data, query) {
    const shopUrl = (window.BookBazarUrls || {}).shop || '/products/';
    let html = '';
    if (data.books.length) {
      html += `<p class="palette-label">${escapeHtml(query ? text.books : text.popular)}</p>`;
      html += data.books.map((book) => `
        <a class="palette-item" role="option" href="${book.url}">
          <img src="${book.cover}" alt="" loading="lazy">
          <span class="palette-text"><strong>${escapeHtml(book.title)}</strong><small>${escapeHtml(book.author)}</small></span>
          <span class="palette-meta">${escapeHtml(formatMoney(book.price))}</span>
        </a>`).join('');
    }
    if (data.categories.length) {
      html += `<p class="palette-label">${escapeHtml(text.categories)}</p>`;
      html += data.categories.map((category) => `
        <a class="palette-item" role="option" href="${category.url}">
          <span class="palette-icon"><i class="fa-solid fa-layer-group"></i></span>
          <span class="palette-text"><strong>${escapeHtml(category.name)}</strong><small>${escapeHtml(text.bookCount.replace('{count}', category.count))}</small></span>
          <i class="fa-solid fa-arrow-right palette-meta"></i>
        </a>`).join('');
    }
    if (query) {
      if (!data.books.length && !data.categories.length) {
        html += `<p class="palette-empty">${escapeHtml(text.noResults.replace('{query}', query))}</p>`;
      }
      html += `
        <a class="palette-item" role="option" href="${shopUrl}?q=${encodeURIComponent(query)}">
          <span class="palette-icon"><i class="fa-solid fa-magnifying-glass"></i></span>
          <span class="palette-text"><strong>${escapeHtml(text.seeAll.replace('{query}', query))}</strong></span>
          <i class="fa-solid fa-arrow-right palette-meta"></i>
        </a>`;
    }
    paletteResults.innerHTML = html;
    setPaletteActive(0);
  }

  function paletteItems() {
    return Array.from(paletteResults.querySelectorAll('.palette-item'));
  }

  function setPaletteActive(index) {
    const items = paletteItems();
    items.forEach((item, i) => item.setAttribute('aria-selected', i === index ? 'true' : 'false'));
    if (items[index]) items[index].scrollIntoView({ block: 'nearest' });
  }

  if (palette) {
    paletteInput.addEventListener('input', () => {
      clearTimeout(paletteTimer);
      paletteTimer = setTimeout(() => loadSuggestions(paletteInput.value.trim()), 140);
    });
    paletteInput.addEventListener('keydown', (event) => {
      const items = paletteItems();
      const current = items.findIndex((item) => item.getAttribute('aria-selected') === 'true');
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        const step = event.key === 'ArrowDown' ? 1 : -1;
        setPaletteActive((current + step + items.length) % items.length);
      } else if (event.key === 'Enter' && items[current]) {
        event.preventDefault();
        items[current].click();
      }
    });
    paletteResults.addEventListener('mousemove', (event) => {
      const item = event.target.closest('.palette-item');
      if (item) setPaletteActive(paletteItems().indexOf(item));
    });
  }

  // Show the platform's own shortcut on the search button
  if (/Mac|iPhone|iPad/.test(navigator.platform)) {
    document.querySelectorAll('[data-shortcut]').forEach((kbd) => { kbd.textContent = '⌘ K'; });
  }

  /* ---------- Cart drawer ---------- */
  const cartDrawer = document.getElementById('cartDrawer');

  async function openCartDrawer() {
    openDialog(cartDrawer);
    try {
      renderCartDrawer(await api(cartDrawer.dataset.miniCartUrl, { method: 'GET' }));
    } catch (error) {
      toast(error.message, 'error');
    }
  }

  function renderCartDrawer(data) {
    const body = cartDrawer.querySelector('[data-drawer-items]');
    const shopUrl = (window.BookBazarUrls || {}).shop || '/products/';
    cartDrawer.querySelector('[data-drawer-count]').textContent = data.total_items || '';
    cartDrawer.querySelector('[data-drawer-foot]').classList.toggle('hidden', !data.items.length);
    cartDrawer.querySelector('[data-drawer-subtotal]').textContent = formatMoney(data.final_total);
    setCartCount(data.total_items);

    if (!data.items.length) {
      body.innerHTML = `<div class="empty"><span class="icon"><i class="fa-solid fa-bag-shopping"></i></span>
        <h3>${escapeHtml(text.cartEmpty)}</h3><p>${escapeHtml(text.cartEmptyHint)}</p>
        <a href="${shopUrl}" class="btn btn-primary">${escapeHtml(text.startShopping)}</a></div>`;
      return;
    }
    body.innerHTML = data.items.map((item) => `
      <div class="drawer-item">
        <a href="${item.url}" class="book-cover"><img src="${item.cover}" alt=""></a>
        <div>
          <a href="${item.url}" class="drawer-item-title">${escapeHtml(item.title)}</a>
          <span class="muted text-sm">${escapeHtml(item.author)}</span>
          <div class="drawer-item-row">
            <span class="text-sm">${escapeHtml(text.qty.replace('{count}', item.quantity))}</span>
            <button type="button" class="link-muted text-sm" data-drawer-remove="${item.id}">${escapeHtml(text.remove)}</button>
          </div>
        </div>
        <strong>${escapeHtml(formatMoney(item.total))}</strong>
      </div>`).join('');
  }

  async function removeFromDrawer(button) {
    const row = button.closest('.drawer-item');
    row.classList.add('is-removing');
    try {
      const url = cartDrawer.dataset.updateUrl.replace('0', button.dataset.drawerRemove);
      const data = await api(url, { body: { action: 'remove' } });
      if (data.success) renderCartDrawer(await api(cartDrawer.dataset.miniCartUrl, { method: 'GET' }));
    } catch (error) {
      row.classList.remove('is-removing');
      toast(error.message, 'error');
    }
  }

  /* ---------- Cover morph between pages ---------- */
  // Name only the clicked cover, so the browser's cross-page view transition can morph it into the book page
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    const card = link && link.closest('.book-card, .palette-item, .hero-slide');
    if (!card || event.metaKey || event.ctrlKey || event.shiftKey) return;
    const img = link.querySelector('img') || card.querySelector('.book-cover img, .hero-slide-cover img');
    if (!img) return;
    // Two elements with the same name would cancel the transition, so release the book page's own cover first
    document.querySelectorAll('.product-media img').forEach((cover) => { cover.style.viewTransitionName = 'none'; });
    img.style.viewTransitionName = 'book-cover';
  }, true);
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('img[style*="view-transition-name"]').forEach((img) => { img.style.viewTransitionName = ''; });
  });

  /* ---------- Hero banner slider ---------- */
  function initSlider(slider) {
    const track = slider.querySelector('[data-slider-track]');
    const slides = Array.from(track.children);
    const dotsBox = slider.querySelector('[data-slider-dots]');
    const toggle = slider.querySelector('[data-slider-toggle]');
    const interval = parseInt(slider.dataset.interval, 10) || 5000;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let index = 0;
    let timer = null;
    let paused = reduceMotion;   // never auto-advance for people who asked for less motion
    let hovering = false;

    if (slides.length < 2) {
      slider.querySelector('.slider-controls').hidden = true;
      return;
    }

    slider.style.setProperty('--slide-interval', `${interval}ms`);
    const dots = slides.map((slide, i) => {
      slide.setAttribute('aria-label', (text.slideOf || '{n} of {total}').replace('{n}', i + 1).replace('{total}', slides.length));
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'slider-dot';
      dot.setAttribute('aria-label', (text.goToSlide || 'Go to slide {n}').replace('{n}', i + 1));
      dot.innerHTML = '<span></span>';
      dot.addEventListener('click', () => { go(i); restart(); });
      dotsBox.appendChild(dot);
      return dot;
    });

    function go(next) {
      index = (next + slides.length) % slides.length;
      track.style.transform = `translateX(-${index * 100}%)`;
      slides.forEach((slide, i) => {
        const active = i === index;
        slide.classList.toggle('is-active', active);
        slide.toggleAttribute('inert', !active);
      });
      dots.forEach((dot, i) => {
        dot.classList.toggle('is-active', i === index);
        dot.setAttribute('aria-current', i === index ? 'true' : 'false');
        // Restart the dot's fill animation so it times the new slide
        const fill = dot.firstElementChild;
        fill.style.animation = 'none';
        void fill.offsetWidth;
        fill.style.animation = '';
      });
    }

    function stop() {
      clearInterval(timer);
      timer = null;
    }

    function restart() {
      stop();
      const running = !paused && !hovering && !document.hidden;
      slider.classList.toggle('is-playing', running);
      if (running) timer = setInterval(() => go(index + 1), interval);
    }

    function setPaused(value) {
      paused = value;
      toggle.innerHTML = `<i class="fa-solid ${paused ? 'fa-play' : 'fa-pause'}"></i>`;
      toggle.setAttribute('aria-label', paused ? toggle.dataset.labelPlay : toggle.dataset.labelPause);
      // While it plays, screen readers are not interrupted by each change
      track.setAttribute('aria-live', paused ? 'polite' : 'off');
      restart();
    }

    slider.querySelector('[data-slider-prev]').addEventListener('click', () => { go(index - 1); restart(); });
    slider.querySelector('[data-slider-next]').addEventListener('click', () => { go(index + 1); restart(); });
    toggle.addEventListener('click', () => setPaused(!paused));

    slider.addEventListener('mouseenter', () => { hovering = true; restart(); });
    slider.addEventListener('mouseleave', () => { hovering = false; restart(); });
    slider.addEventListener('focusin', () => { hovering = true; restart(); });
    slider.addEventListener('focusout', (event) => {
      if (!slider.contains(event.relatedTarget)) { hovering = false; restart(); }
    });
    document.addEventListener('visibilitychange', restart);

    slider.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowRight') { go(index + 1); restart(); }
      if (event.key === 'ArrowLeft') { go(index - 1); restart(); }
    });

    // Swipe on touch screens
    let startX = null;
    slider.addEventListener('pointerdown', (event) => {
      if (event.pointerType !== 'mouse') startX = event.clientX;
    });
    slider.addEventListener('pointerup', (event) => {
      if (startX === null) return;
      const distance = event.clientX - startX;
      startX = null;
      if (Math.abs(distance) > 40) { go(index + (distance < 0 ? 1 : -1)); restart(); }
    });

    go(0);
    setPaused(paused);
  }

  document.querySelectorAll('[data-slider]').forEach(initSlider);

  /* ---------- Sticky buy bar ---------- */
  const buyBar = document.querySelector('.buy-bar');
  const buyBox = document.querySelector('.buy-box');
  if (buyBar && buyBox && 'IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => {
      buyBar.classList.toggle('is-visible', !entry.isIntersecting && entry.boundingClientRect.top < 0);
    }).observe(buyBox);
  }

  function setMobileNav(open) {
    const nav = document.querySelector('.mobile-nav');
    if (!nav) return;
    nav.classList.toggle('is-open', open);
    document.body.style.overflow = open ? 'hidden' : '';
    const icon = document.querySelector('[data-nav-toggle] i');
    if (icon) icon.className = `fa-solid ${open ? 'fa-xmark' : 'fa-bars'}`;
  }

  function closeMobileNav() {
    setMobileNav(false);
  }

  /* ---------- Event delegation ---------- */
  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-search-open]')) {
      event.preventDefault();
      openPalette();
      return;
    }

    const cartLink = event.target.closest('[data-cart-open]');
    if (cartLink && cartDrawer && !event.metaKey && !event.ctrlKey) {
      event.preventDefault();
      openCartDrawer();
      return;
    }

    if (event.target.closest('[data-drawer-close]')) {
      closeDialog(cartDrawer);
      return;
    }

    const regionPicker = document.getElementById('regionPicker');
    if (event.target.closest('[data-region-open]') && regionPicker) {
      closeMobileNav();
      openDialog(regionPicker);
      return;
    }

    const dialogClose = event.target.closest('[data-dialog-close]');
    if (dialogClose) {
      closeDialog(dialogClose.closest('dialog'));
      return;
    }

    const copyButton = event.target.closest('[data-copy]');
    if (copyButton) {
      navigator.clipboard.writeText(copyButton.dataset.copy).then(() => {
        copyButton.classList.add('is-copied');
        toast(copyButton.dataset.copied, 'success', { timeout: 2000 });
        setTimeout(() => copyButton.classList.remove('is-copied'), 1500);
      }).catch(() => {});
      return;
    }

    const drawerRemove = event.target.closest('[data-drawer-remove]');
    if (drawerRemove) {
      removeFromDrawer(drawerRemove);
      return;
    }

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
      setMobileNav(!nav.classList.contains('is-open'));
      return;
    }

    // Close open dropdown menus when clicking elsewhere
    document.querySelectorAll('details.menu[open]').forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute('open');
    });
  });

  document.addEventListener('keydown', (event) => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
    if ((event.key === 'k' && (event.metaKey || event.ctrlKey)) || (event.key === '/' && !typing)) {
      event.preventDefault();
      openPalette();
      return;
    }
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

  window.BookBazar = { api, toast, setLoading, setCartCount, csrfToken, formatMoney };
})();
