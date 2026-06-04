(() => {
  'use strict';

  const STORE_KEY = 'compass-deck-media-v4';
  const VIDEO_WARN_BYTES = 3 * 1024 * 1024;
  const BOX_SCALE_MIN = 0.35;
  const BOX_SCALE_MAX = 1;
  const BOX_HEIGHT_MIN = 0.55;
  const BOX_HEIGHT_MAX = 1.65;
  const DEFAULT_HEIGHT = 1;

  const slides = Array.from(document.querySelectorAll('.slide'));
  const dotsEl = document.getElementById('dots');
  const counterEl = document.getElementById('counter');
  const toastEl = document.getElementById('toast');
  let current = 0;
  let activeResize = null;

  let media = loadMedia();

  function slotEntry(partial) {
    const items = (partial.items || []).filter((i) => i?.src);
    if (!items.length) return null;

    let boxHeightScale = Number(partial.boxHeightScale);
    if (!Number.isFinite(boxHeightScale) && partial.boxAspect) {
      boxHeightScale = 1.6 / Number(partial.boxAspect);
    }

    const index = Math.max(0, Math.min(items.length - 1, Number(partial.index) || 0));
    return {
      items: items.map((i) => ({
        src: i.src,
        type: i.type === 'video' ? 'video' : 'image',
      })),
      index,
      fit: partial.fit === 'cover' ? 'cover' : 'contain',
      boxScale: clampBoxScale(Number(partial.boxScale) || BOX_SCALE_MAX),
      boxHeightScale: clampHeight(boxHeightScale || DEFAULT_HEIGHT),
    };
  }

  function normalizeEntry(raw) {
    if (!raw) return null;
    if (typeof raw === 'string') {
      return slotEntry({ items: [{ src: raw, type: 'image' }] });
    }
    if (Array.isArray(raw.items)) {
      return slotEntry(raw);
    }
    if (raw.src) {
      return slotEntry({
        items: [{ src: raw.src, type: raw.type === 'video' ? 'video' : 'image' }],
        index: 0,
        fit: raw.fit,
        boxScale: raw.boxScale,
        boxHeightScale: raw.boxHeightScale,
        boxAspect: raw.boxAspect,
      });
    }
    return null;
  }

  function loadMedia() {
    try {
      let raw = localStorage.getItem(STORE_KEY);
      if (!raw) {
        raw = localStorage.getItem('compass-deck-media-v3')
          || localStorage.getItem('compass-deck-media-v2')
          || localStorage.getItem('compass-deck-media-v1');
      }
      const parsed = JSON.parse(raw || '{}') || {};
      const out = {};
      for (const [id, val] of Object.entries(parsed)) {
        const entry = normalizeEntry(val);
        if (entry) out[id] = entry;
      }
      return out;
    } catch {
      return {};
    }
  }

  function saveMedia() {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify(media));
    } catch {
      toast('Could not save to browser storage (~5MB limit). Use Export media.');
    }
  }

  function clampBoxScale(n) {
    return Math.min(BOX_SCALE_MAX, Math.max(BOX_SCALE_MIN, Math.round(n * 100) / 100));
  }

  function clampHeight(n) {
    return Math.min(BOX_HEIGHT_MAX, Math.max(BOX_HEIGHT_MIN, Math.round(n * 100) / 100));
  }

  function getHost(slot) {
    const p = slot.parentElement;
    return p?.classList.contains('media-host') ? p : null;
  }

  function getBar(slot) {
    return slot.closest('.media-wrap')?.querySelector('.media-bar') ?? null;
  }

  function currentItem(entry) {
    return entry.items[entry.index];
  }

  /* ---------------- Slide navigation ---------------- */
  function show(i) {
    current = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach((s, idx) => s.classList.toggle('active', idx === current));
    Array.from(dotsEl.children).forEach((d, idx) => d.classList.toggle('active', idx === current));
    counterEl.textContent = `${current + 1} / ${slides.length}`;
    history.replaceState(null, '', `#${current + 1}`);
  }
  const next = () => show(current + 1);
  const prev = () => show(current - 1);

  slides.forEach((s, idx) => {
    const dot = document.createElement('button');
    dot.className = 'dot';
    dot.title = s.dataset.title || `Slide ${idx + 1}`;
    dot.setAttribute('aria-label', dot.title);
    dot.addEventListener('click', () => show(idx));
    dotsEl.appendChild(dot);
  });

  document.getElementById('btn-next').addEventListener('click', next);
  document.getElementById('btn-prev').addEventListener('click', prev);

  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea, select')) return;
    switch (e.key) {
      case 'ArrowRight': case 'PageDown': case ' ': next(); e.preventDefault(); break;
      case 'ArrowLeft': case 'PageUp': prev(); break;
      case 'Home': show(0); break;
      case 'End': show(slides.length - 1); break;
      case 'f': case 'F': toggleFullscreen(); break;
    }
  });

  /* ---------------- Media slots ---------------- */
  const slotEls = Array.from(document.querySelectorAll('.media-slot'));
  slotEls.forEach(ensureWrap);
  slotEls.forEach(initSlot);

  document.addEventListener('mousemove', onResizeMove);
  document.addEventListener('mouseup', endResize);

  function ensureWrap(slot) {
    if (slot.closest('.media-wrap')) return;
    const wrap = document.createElement('div');
    wrap.className = 'media-wrap';
    const host = document.createElement('div');
    host.className = 'media-host';
    if (slot.classList.contains('media-slot-sm')) {
      host.classList.add('media-host-sm');
    }
    const parent = slot.parentNode;
    parent.insertBefore(wrap, slot);
    host.appendChild(slot);
    wrap.appendChild(host);
    const bar = document.createElement('div');
    bar.className = 'media-bar';
    bar.hidden = true;
    wrap.appendChild(bar);
  }

  function initSlot(slot) {
    renderSlot(slot);

    const wrap = slot.closest('.media-wrap');
    if (wrap) {
      wrap.addEventListener('click', (e) => {
        const act = e.target.dataset.act;
        if (!act) return;
        e.stopPropagation();
        handleAction(slot, act);
      });
    }

    slot.addEventListener('click', (e) => {
      if (e.target.closest('[data-act="resize-handle"], .media-nav, .media-bar')) return;
      const slotId = slot.dataset.slot;
      if (!slotId || !media[slotId]) {
        pickFiles(slot, { mode: 'add' });
      }
    });

    slot.addEventListener('mousedown', (e) => {
      const handle = e.target.closest('[data-act="resize-handle"]');
      if (!handle) return;
      const slotId = slot.dataset.slot;
      if (!slotId || !media[slotId]) return;
      e.preventDefault();
      e.stopPropagation();
      startResize(e, slot, slotId);
    });

    slot.addEventListener('dragover', (e) => {
      e.preventDefault();
      slot.classList.add('dragover');
    });
    slot.addEventListener('dragleave', () => slot.classList.remove('dragover'));
    slot.addEventListener('drop', (e) => {
      e.preventDefault();
      slot.classList.remove('dragover');
      const files = Array.from(e.dataTransfer.files || []);
      if (files.length) readFiles(slot, files, { mode: media[slot.dataset.slot] ? 'append' : 'add' });
    });
  }

  function handleAction(slot, act) {
    const slotId = slot.dataset.slot;
    const entry = media[slotId];
    if (!entry && act !== 'add') return;

    if (act === 'media-prev') {
      if (entry.index > 0) {
        entry.index -= 1;
        saveMedia();
        renderSlot(slot);
      }
      return;
    }
    if (act === 'media-next') {
      if (entry.index < entry.items.length - 1) {
        entry.index += 1;
        saveMedia();
        renderSlot(slot);
      }
      return;
    }
    if (act === 'remove') {
      entry.items.splice(entry.index, 1);
      if (!entry.items.length) {
        delete media[slotId];
      } else {
        entry.index = Math.min(entry.index, entry.items.length - 1);
      }
      saveMedia();
      renderSlot(slot);
      return;
    }
    if (act === 'remove-all') {
      delete media[slotId];
      saveMedia();
      renderSlot(slot);
      return;
    }
    if (act === 'add') {
      pickFiles(slot, { mode: 'append' });
      return;
    }
    if (act === 'replace') {
      pickFiles(slot, { mode: 'replace' });
      return;
    }
    if (act === 'box-reset') {
      entry.boxScale = BOX_SCALE_MAX;
      entry.boxHeightScale = DEFAULT_HEIGHT;
      saveMedia();
      renderSlot(slot);
      return;
    }
    if (act === 'fit-toggle') {
      entry.fit = entry.fit === 'cover' ? 'contain' : 'cover';
      saveMedia();
      applyBoxSize(slot, entry);
      renderBar(slot, entry);
    }
  }

  function pickFiles(targetSlot, { mode = 'add' } = {}) {
    const inp = document.createElement('input');
    inp.type = 'file';
    inp.multiple = mode !== 'replace';
    inp.accept = 'image/*,video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov';
    inp.addEventListener('change', () => {
      const files = Array.from(inp.files || []);
      if (!files.length) return;
      readFiles(targetSlot, files, { mode });
    });
    inp.click();
  }

  function readFiles(targetSlot, files, { mode = 'add' }) {
    const slotId = targetSlot.dataset.slot;
    const valid = files.filter((f) => f.type.startsWith('image/') || f.type.startsWith('video/'));
    if (!valid.length) {
      toast('Use images (PNG, JPG, GIF, WEBP) or videos (MP4, WebM, MOV).');
      return;
    }
    valid.forEach((f) => {
      if (f.type.startsWith('video/') && f.size > VIDEO_WARN_BYTES) {
        toast('Large video — storage may fail. Prefer clips under ~3MB.');
      }
    });

    Promise.all(valid.map((file) => new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve({
        src: reader.result,
        type: file.type.startsWith('video/') ? 'video' : 'image',
      });
      reader.onerror = reject;
      reader.readAsDataURL(file);
    }))).then((newItems) => {
      const prev = media[slotId];
      if (mode === 'replace' && prev) {
        prev.items[prev.index] = newItems[0];
        if (newItems.length > 1) {
          prev.items.splice(prev.index + 1, 0, ...newItems.slice(1));
        }
        media[slotId] = prev;
      } else if (prev) {
        prev.items.push(...newItems);
        prev.index = prev.items.length - newItems.length;
        media[slotId] = prev;
      } else {
        media[slotId] = slotEntry({
          items: newItems,
          index: 0,
        });
      }
      saveMedia();
      renderSlot(targetSlot);
      if (newItems.length > 1) {
        toast(`Added ${newItems.length} files. Use ‹ › to browse.`);
      }
    }).catch(() => toast('Could not read one or more files.'));
  }

  function applyBoxSize(slot, entry) {
    slot.style.width = `${Math.round(entry.boxScale * 100)}%`;
    slot.style.height = `${Math.round(entry.boxHeightScale * 100)}%`;
    slot.style.aspectRatio = 'unset';
    const content = slot.querySelector('.media-content');
    if (content) content.style.objectFit = entry.fit;
  }

  function renderBar(slot, entry) {
    const bar = getBar(slot);
    if (!bar || !entry?.items?.length) return;
    const fitLabel = entry.fit === 'cover' ? 'Cover' : 'Contain';
    const wPct = Math.round(entry.boxScale * 100);
    const hPct = Math.round(entry.boxHeightScale * 100);
    const multi = entry.items.length > 1;
    bar.hidden = false;
    bar.innerHTML =
      (multi
        ? `<span class="media-gallery-nav">` +
            `<button type="button" data-act="media-prev" class="media-bar-btn media-bar-nav" ${entry.index === 0 ? 'disabled' : ''} aria-label="Previous image">‹</button>` +
            `<span class="media-bar-count">${entry.index + 1} / ${entry.items.length}</span>` +
            `<button type="button" data-act="media-next" class="media-bar-btn media-bar-nav" ${entry.index === entry.items.length - 1 ? 'disabled' : ''} aria-label="Next image">›</button>` +
          `</span>`
        : '') +
      `<span class="media-bar-size">${wPct}% × ${hPct}%</span>` +
      `<span class="media-bar-hint">${multi ? '‹ › or side arrows' : 'Drag corner to resize'}</span>` +
      `<span class="media-bar-spacer"></span>` +
      `<button type="button" data-act="add" class="media-bar-btn">Add</button>` +
      `<button type="button" data-act="box-reset" class="media-bar-btn">Reset</button>` +
      `<button type="button" data-act="fit-toggle" class="media-bar-btn">${fitLabel}</button>` +
      `<button type="button" data-act="replace" class="media-bar-btn">Replace</button>` +
      `<button type="button" data-act="remove" class="media-bar-btn">${multi ? 'Remove this' : 'Remove'}</button>` +
      (multi ? `<button type="button" data-act="remove-all" class="media-bar-btn">Clear all</button>` : '');
  }

  function mediaTagFor(item, id, index) {
    if (item.type === 'video') {
      return `<video class="media-content" src="${item.src}" autoplay loop muted playsinline></video>`;
    }
    return `<img class="media-content" src="${item.src}" alt="${id}-${index + 1}" />`;
  }

  function navHtml(entry) {
    if (entry.items.length <= 1) return '';
    const atStart = entry.index === 0;
    const atEnd = entry.index === entry.items.length - 1;
    return (
      `<button type="button" class="media-nav media-nav-prev" data-act="media-prev" ${atStart ? 'disabled' : ''} aria-label="Previous image">‹</button>` +
      `<button type="button" class="media-nav media-nav-next" data-act="media-next" ${atEnd ? 'disabled' : ''} aria-label="Next image">›</button>` +
      `<div class="media-badge">${entry.index + 1} / ${entry.items.length}</div>`
    );
  }

  function startResize(e, slot, slotId) {
    const host = getHost(slot);
    if (!host) return;
    activeResize = {
      slot,
      slotId,
      hostW: host.clientWidth,
      hostH: host.clientHeight,
      startX: e.clientX,
      startY: e.clientY,
      startW: host.clientWidth * media[slotId].boxScale,
      startH: host.clientHeight * media[slotId].boxHeightScale,
    };
    slot.classList.add('resizing');
  }

  function onResizeMove(e) {
    if (!activeResize) return;
    const { slot, slotId, hostW, hostH, startX, startY, startW, startH } = activeResize;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    const newW = Math.max(hostW * BOX_SCALE_MIN, Math.min(hostW, startW + dx));
    const newH = Math.max(hostH * BOX_HEIGHT_MIN, Math.min(hostH, startH + dy));
    media[slotId].boxScale = clampBoxScale(newW / hostW);
    media[slotId].boxHeightScale = clampHeight(newH / hostH);
    applyBoxSize(slot, media[slotId]);
    renderBar(slot, media[slotId]);
  }

  function endResize() {
    if (!activeResize) return;
    activeResize.slot.classList.remove('resizing');
    saveMedia();
    activeResize = null;
  }

  function renderSlot(slot) {
    const id = slot.dataset.slot;
    const label = slot.dataset.label || 'Click or drop media';
    const entry = media[id];
    const bar = getBar(slot);

    slot.style.width = '';
    slot.style.height = '';
    slot.style.aspectRatio = '';

    if (entry?.items?.length) {
      slot.classList.add('filled');
      if (entry.items.length > 1) slot.classList.add('has-gallery');
      else slot.classList.remove('has-gallery');

      const item = currentItem(entry);
      slot.innerHTML =
        `<div class="media-viewport">${mediaTagFor(item, id, entry.index)}</div>` +
        navHtml(entry) +
        `<div class="resize-handle" data-act="resize-handle" title="Drag to resize frame"></div>`;

      applyBoxSize(slot, entry);
      renderBar(slot, entry);
    } else {
      slot.classList.remove('filled', 'has-gallery');
      if (bar) bar.hidden = true;
      slot.style.width = '100%';
      slot.style.height = '100%';
      slot.innerHTML =
        `<div class="media-hint">` +
          `<span class="plus">＋</span>${label}` +
          `<br><small>click or drag &amp; drop · multiple files OK</small>` +
          `<br><small class="hint-sub">PNG · JPG · GIF · WEBP · MP4 · WebM · MOV</small>` +
        `</div>`;
    }
  }

  function refreshAllSlots() {
    slotEls.forEach(renderSlot);
  }

  /* ---------------- Export / import ---------------- */
  document.getElementById('btn-export').addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(media, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'compass-deck-media.json';
    a.click();
    URL.revokeObjectURL(a.href);
    toast('Exported media to compass-deck-media.json');
  });

  const importFile = document.getElementById('import-file');
  document.getElementById('btn-import').addEventListener('click', () => importFile.click());
  importFile.addEventListener('change', () => {
    const file = importFile.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(reader.result) || {};
        media = {};
        for (const [id, val] of Object.entries(parsed)) {
          const entry = normalizeEntry(val);
          if (entry) media[id] = entry;
        }
        saveMedia();
        refreshAllSlots();
        toast('Imported media.');
      } catch {
        toast('That file is not a valid media export.');
      }
    };
    reader.readAsText(file);
    importFile.value = '';
  });

  function toggleFullscreen() {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
    else document.exitFullscreen?.();
  }
  document.getElementById('btn-fs').addEventListener('click', toggleFullscreen);

  let toastTimer;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastEl.hidden = true; }, 4200);
  }

  const fromHash = parseInt(location.hash.replace('#', ''), 10);
  show(Number.isFinite(fromHash) ? fromHash - 1 : 0);
})();
