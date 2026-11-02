// Helpers shared by every page script (loaded as an ES module).

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

/** Escape text before putting it into innerHTML, so user input can never inject markup. */
export function esc(value) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(value ?? '').replace(/[&<>"']/g, (c) => map[c]);
}

/**
 * Talk to the Flask API.
 *  - { json }  -> sent as application/json
 *  - { form }  -> a FormData object, sent as multipart/form-data (the browser adds the boundary)
 * Always resolves to { ok, status, data }; it never throws on HTTP errors.
 */
export async function api(path, { method = 'GET', json, form } = {}) {
  const init = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
  if (json !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(json);
  } else if (form) {
    init.body = form;
  }
  try {
    const res = await fetch(path, init);
    let data = {};
    try { data = await res.json(); } catch { /* empty body */ }
    return { ok: res.ok, status: res.status, data };
  } catch {
    return { ok: false, status: 0, data: { error: 'Cannot reach the server. Check your connection and try again.' } };
  }
}

// ---------------------------------------------------------------- icons
const svg = (body, cls = '') =>
  `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${body}</svg>`;

const ICONS = {
  pin: '<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  user: '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
  box: '<path d="M3.5 8L12 4l8.5 4v8L12 20l-8.5-4z"/><path d="M3.5 8L12 12l8.5-4M12 12v8"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3.5 7l8.5 6 8.5-6"/>',
  phone: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A15 15 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
  tag: '<path d="M3.5 12V4.5H11l9.5 9.5-7 7z"/><circle cx="7.8" cy="8.3" r="1.1"/>',
  // category icons
  Electronics: '<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
  'Documents & ID': '<rect x="3" y="5" width="18" height="14" rx="2.5"/><circle cx="9" cy="11" r="2"/><path d="M6 16c.6-1.6 5.4-1.6 6 0M14.5 10h3.5M14.5 13.5h3.5"/>',
  'Books & Stationery': '<path d="M4.5 4.5h11a3 3 0 0 1 3 3V20H7.5a3 3 0 0 1-3-3z"/><path d="M4.5 17a3 3 0 0 1 3-3h11"/>',
  'Bags & Clothing': '<path d="M9 6.5a3 3 0 0 1 6 0"/><rect x="5" y="7" width="14" height="14" rx="3.5"/><path d="M9 13h6M9 16.5h6"/>',
  Keys: '<circle cx="8" cy="15.5" r="4"/><path d="M11 12.5l9-9M16 7.5l3 3"/>',
  'Wallet & Money': '<path d="M3.5 7.5a2 2 0 0 1 2-2H18v3.5"/><rect x="3.5" y="7.5" width="17" height="12.5" rx="2.5"/><circle cx="16.3" cy="13.8" r="1.1"/>',
  Other: '<path d="M3.5 12V4.5H11l9.5 9.5-7 7z"/><circle cx="7.8" cy="8.3" r="1.1"/>',
};

export const icon = (name, cls = '') => svg(ICONS[name] || ICONS.Other, cls);
export const categoryIcon = (category, cls = '') => icon(ICONS[category] ? category : 'Other', cls);

// ---------------------------------------------------------------- formatting
export const tagNo = (id) => 'No. ' + String(id).padStart(4, '0');

export function formatDate(isoDate) {
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

/** created_at values are UTC strings like "2026-10-29 11:05:00". */
export function timeAgo(sqlUtc) {
  const then = new Date(sqlUtc.replace(' ', 'T') + 'Z');
  const seconds = Math.max(0, (Date.now() - then.getTime()) / 1000);
  const steps = [[60, 'second'], [60, 'minute'], [24, 'hour'], [30, 'day'], [12, 'month'], [Infinity, 'year']];
  let value = seconds;
  for (const [size, unit] of steps) {
    if (value < size) {
      const n = Math.floor(value);
      if (unit === 'second') return 'just now';
      return `${n} ${unit}${n === 1 ? '' : 's'} ago`;
    }
    value /= size;
  }
  return formatDate(sqlUtc.slice(0, 10));
}

export const todayIso = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

// ---------------------------------------------------------------- UI feedback
export function toast(message, variant = 'success') {
  const area = document.getElementById('toastArea');
  if (!area || !window.bootstrap) return;
  const el = document.createElement('div');
  el.className = `toast align-items-center text-bg-${variant} border-0`;
  el.setAttribute('role', variant === 'danger' ? 'alert' : 'status');
  el.innerHTML = `<div class="d-flex"><div class="toast-body">${esc(message)}</div>
    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
  area.appendChild(el);
  el.addEventListener('hidden.bs.toast', () => el.remove());
  window.bootstrap.Toast.getOrCreateInstance(el, { delay: 4500 }).show();
}

export function showAlert(el, message) {
  if (!el) return;
  el.textContent = message;
  el.classList.remove('d-none');
}
export const hideAlert = (el) => el && el.classList.add('d-none');

export function setBusy(button, busy, busyText = 'Please wait…') {
  if (!button) return;
  if (busy) {
    button.dataset.label = button.textContent;
    button.textContent = busyText;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.label || button.textContent;
    button.disabled = false;
  }
}

// ---------------------------------------------------------------- form validation
/** Show (or clear, with an empty message) the error under one field. */
export function setFieldError(form, name, message) {
  const control = form.elements.namedItem(name);
  const feedback = form.querySelector(`#${CSS.escape(name)}-error`);
  if (!control) return false;
  const controls = control instanceof RadioNodeList ? [...control] : [control];
  const group = controls[0].closest('.type-tiles');
  controls.forEach((c) => {
    c.classList.toggle('is-invalid', Boolean(message));
    if (message) c.setAttribute('aria-invalid', 'true'); else c.removeAttribute('aria-invalid');
  });
  if (group) group.classList.toggle('is-invalid-group', Boolean(message));
  if (feedback) {
    feedback.textContent = message || '';
    feedback.classList.toggle('d-block', Boolean(message));
  }
  return true;
}

export function clearErrors(form) {
  $$('input, select, textarea', form).forEach((c) => c.name && setFieldError(form, c.name, ''));
}

function friendlyMessage(field) {
  const v = field.validity;
  if (v.customError) return field.validationMessage;
  if (v.valueMissing) {
    if (field.tagName === 'SELECT') return 'Please choose an option.';
    if (field.type === 'date') return 'Please pick a date.';
    return 'This field is required.';
  }
  if (v.typeMismatch && field.type === 'email') return 'Enter a valid email address, like name@example.com.';
  if (v.tooShort) return `Use at least ${field.minLength} characters.`;
  if (v.tooLong) return `Use at most ${field.maxLength} characters.`;
  if (v.rangeOverflow) return 'The date cannot be in the future.';
  if (v.rangeUnderflow) return 'The date cannot be more than a year ago.';
  return field.validationMessage || 'Please check this field.';
}

/**
 * Client-side validation using the browser's Constraint Validation API (the required,
 * minlength, type=email, min/max attributes in the HTML) plus any setCustomValidity() rules.
 * Returns true when the form may be submitted; otherwise shows messages and focuses the first problem.
 */
export function validateForm(form) {
  let first = null;
  const seenRadios = new Set();
  for (const field of $$('input, select, textarea', form)) {
    if (!field.name || field.disabled || field.type === 'hidden' || field.type === 'file') continue;
    if (field.type === 'radio') {
      if (seenRadios.has(field.name)) continue;
      seenRadios.add(field.name);
      const group = form.elements.namedItem(field.name);
      const chosen = [...group].some((r) => r.checked);
      const required = [...group].some((r) => r.required);
      setFieldError(form, field.name, required && !chosen ? 'Please choose one option.' : '');
      if (required && !chosen && !first) first = field;
      continue;
    }
    const valid = field.checkValidity();
    setFieldError(form, field.name, valid ? '' : friendlyMessage(field));
    if (!valid && !first) first = field;
  }
  if (first) first.focus();
  return !first;
}

/** Show the field errors returned by the server (HTTP 422). Returns true if every one was placed. */
export function showServerErrors(form, errors = {}) {
  let first = null;
  let allPlaced = true;
  for (const [name, message] of Object.entries(errors)) {
    if (setFieldError(form, name, message)) {
      if (!first) first = form.elements.namedItem(name);
    } else {
      allPlaced = false;
    }
  }
  const target = first instanceof RadioNodeList ? first[0] : first;
  if (target) target.focus();
  return allPlaced;
}

// ---------------------------------------------------------------- item rendering
export const statusPill = (status) =>
  `<span class="pill pill-${esc(status)}">${{ open: 'Open', resolved: 'Returned', pending: 'Pending', approved: 'Approved', rejected: 'Declined' }[status] || esc(status)}</span>`;

/**
 * One item as a "claim tag" card. With options.href the call-to-action is a link;
 * otherwise it is a button carrying data-item-id for the page script to handle.
 */
export function itemCard(item, { href } = {}) {
  const lost = item.type === 'lost';
  const resolved = item.status === 'resolved';
  const label = `View details for ${item.title}`;
  const cta = href
    ? `<a class="btn btn-sm btn-primary stretched-link" href="${esc(href)}" aria-label="${esc(label)}">View details</a>`
    : `<button type="button" class="btn btn-sm btn-primary stretched-link" data-item-id="${item.id}" aria-label="${esc(label)}">View details</button>`;
  const photo = item.image_url
    ? `<img src="${esc(item.image_url)}" alt="Photo of ${esc(item.title)}" loading="lazy">`
    : categoryIcon(item.category);
  return `
    <article class="tag-card${resolved ? ' is-resolved' : ''}">
      <div class="tag-head ${lost ? 'lost' : 'found'}">
        <span>${lost ? 'Lost' : 'Found'}</span>
        ${resolved ? '<span class="tag-returned">Returned</span>' : ''}
        <span class="tag-no">${tagNo(item.id)}</span>
      </div>
      <div class="tag-photo">${photo}</div>
      <div class="tag-body">
        <h3 class="tag-title">${esc(item.title)}</h3>
        <ul class="tag-facts">
          <li>${icon('pin')}<span>${esc(item.location)}</span></li>
          <li>${icon('calendar')}<span>${formatDate(item.event_date)}</span></li>
        </ul>
      </div>
      <div class="tag-foot">
        <span class="tag-cat">${categoryIcon(item.category)}<span class="text-truncate">${esc(item.category)}</span></span>
        ${cta}
      </div>
    </article>`;
}

export function emptyState(title, text, actionHtml = '') {
  return `<div class="col-12"><div class="empty-state">${icon('box')}<h2 class="h4 mt-2">${esc(title)}</h2>
    <p class="text-muted mx-auto">${esc(text)}</p>${actionHtml}</div></div>`;
}

/** Ask the user to confirm an action in the page's #confirmModal. Resolves to true/false. */
export function confirmDialog({ title, text, okLabel, okClass = 'btn-primary' }) {
  return new Promise((resolve) => {
    const modalEl = document.getElementById('confirmModal');
    const ok = modalEl.querySelector('#confirmOk, #confirmDelete');
    modalEl.querySelector('h2').textContent = title;
    const p = modalEl.querySelector('p');
    if (p) p.textContent = text;
    ok.textContent = okLabel;
    ok.className = `btn ${okClass}`;
    const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
    let decided = false;
    const done = (value) => { decided = true; modal.hide(); resolve(value); };
    ok.addEventListener('click', () => done(true), { once: true });
    modalEl.addEventListener('hidden.bs.modal', () => { if (!decided) resolve(false); }, { once: true });
    modal.show();
  });
}
