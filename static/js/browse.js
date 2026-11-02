// MODULE 3 (Student 2): browse, search, filter, paginate, view details and send a claim.
import {
  $, $$, api, categoryIcon, emptyState, esc, formatDate, hideAlert, icon, itemCard,
  setFieldError, showAlert, showServerErrors, statusPill, tagNo, timeAgo, toast, validateForm,
} from './common.js';

const form = $('#filterForm');
const results = $('#results');
const countEl = $('#resultCount');
const pager = $('#pagerNav');
const clearBtn = $('#clearFilters');
const loggedIn = Boolean(document.body.dataset.userId);
const PER_PAGE = 9;

let page = 1;
let requestId = 0;      // ignore responses that arrive after a newer request was sent

// ------------------------------------------------------------ filters <-> URL
function restoreFromUrl() {
  const p = new URLSearchParams(window.location.search);
  ['q', 'category', 'sort'].forEach((key) => { if (p.get(key)) form.elements[key].value = p.get(key); });
  const type = $(`input[name="type"][value="${p.get('type')}"]`, form);
  if (type) type.checked = true;
  form.elements.resolved.checked = p.get('resolved') === '1';
  page = Math.max(parseInt(p.get('page') || '1', 10) || 1, 1);
}

function currentQuery() {
  const query = new URLSearchParams();
  for (const [key, value] of new FormData(form)) if (value) query.set(key, value);
  if (query.get('sort') === 'newest') query.delete('sort');
  if (page > 1) query.set('page', String(page));
  return query;
}

// ------------------------------------------------------------ load + render the grid
async function load() {
  const myRequest = ++requestId;
  const query = currentQuery();
  results.setAttribute('aria-busy', 'true');

  const apiQuery = new URLSearchParams(query);
  apiQuery.set('per_page', String(PER_PAGE));
  const { ok, data } = await api(`/api/items?${apiQuery}`);
  if (myRequest !== requestId) return;

  window.history.replaceState(null, '', query.toString() ? `?${query}` : window.location.pathname);
  clearBtn.classList.toggle('d-none', ![...query.keys()].some((k) => k !== 'page'));

  if (!ok) {
    results.innerHTML = emptyState('Items could not be loaded', data.error || 'Please try again in a moment.');
    countEl.textContent = '';
    pager.innerHTML = '';
    results.removeAttribute('aria-busy');
    return;
  }

  if (page > data.pages) {       // e.g. results shrank while on a later page
    page = data.pages;
    return load();
  }

  countEl.textContent = data.total === 0
    ? 'No items match your search.'
    : `${data.total} item${data.total === 1 ? '' : 's'} found${data.pages > 1 ? `, page ${data.page} of ${data.pages}` : ''}`;

  results.innerHTML = data.items.length
    ? data.items.map((item) => `<div class="col-sm-6 col-lg-4">${itemCard(item)}</div>`).join('')
    : emptyState(
      'Nothing matches yet',
      'Try a different word or clear the filters. If you lost something, report it so finders can reach you.',
      '<a class="btn btn-lost" href="/report?type=lost">Report a lost item</a>',
    );
  results.removeAttribute('aria-busy');
  renderPager(data.page, data.pages);
}

function renderPager(current, total) {
  if (total <= 1) { pager.innerHTML = ''; return; }
  const pages = new Set([1, total, current - 1, current, current + 1]);
  const list = [...pages].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b);
  const items = [];
  items.push(current > 1
    ? `<li class="page-item"><button class="page-link" data-page="${current - 1}">Previous</button></li>`
    : '<li class="page-item disabled"><span class="page-link">Previous</span></li>');
  list.forEach((n, i) => {
    if (i > 0 && n - list[i - 1] > 1) items.push('<li class="page-item disabled"><span class="page-link">&hellip;</span></li>');
    items.push(n === current
      ? `<li class="page-item active" aria-current="page"><span class="page-link">${n}</span></li>`
      : `<li class="page-item"><button class="page-link" data-page="${n}" aria-label="Page ${n}">${n}</button></li>`);
  });
  items.push(current < total
    ? `<li class="page-item"><button class="page-link" data-page="${current + 1}">Next</button></li>`
    : '<li class="page-item disabled"><span class="page-link">Next</span></li>');
  pager.innerHTML = `<ul class="pagination mb-0">${items.join('')}</ul>`;
}

pager.addEventListener('click', (event) => {
  const button = event.target.closest('[data-page]');
  if (!button) return;
  page = Number(button.dataset.page);
  load();
  form.scrollIntoView({ behavior: 'smooth', block: 'start' });
});

// search box is debounced; every other control reloads immediately
let timer;
form.addEventListener('input', (event) => {
  if (event.target.name !== 'q') return;
  clearTimeout(timer);
  timer = setTimeout(() => { page = 1; load(); }, 300);
});
form.addEventListener('change', (event) => {
  if (event.target.name === 'q') return;
  page = 1;
  load();
});
form.addEventListener('submit', (event) => { event.preventDefault(); page = 1; load(); });
clearBtn.addEventListener('click', () => { form.reset(); page = 1; load(); });

// ------------------------------------------------------------ item details modal
const modalEl = $('#itemModal');
const modal = window.bootstrap.Modal.getOrCreateInstance(modalEl);
const modalBody = $('#itemModalBody');
const modalHead = $('#itemModalHead');

results.addEventListener('click', (event) => {
  const trigger = event.target.closest('[data-item-id]');
  if (trigger) openItem(trigger.dataset.itemId);
});

async function openItem(id) {
  modalBody.innerHTML = '<p class="text-muted mb-0">Loading&hellip;</p>';
  modal.show();
  await refreshItem(id);
}

async function refreshItem(id) {
  const { ok, data } = await api(`/api/items/${id}`);
  if (!ok) {
    modalBody.innerHTML = `<div class="alert alert-danger mb-0" role="alert">${esc(data.error || 'This item could not be loaded.')}</div>`;
    return;
  }
  renderItem(data.item);
}

function contactCard(name, contact) {
  const email = contact.email ? `<div>${icon('mail', 'me-1')}<a href="mailto:${esc(contact.email)}">${esc(contact.email)}</a></div>` : '';
  const phone = contact.phone ? `<div>${icon('phone', 'me-1')}<a href="tel:${esc(contact.phone)}">${esc(contact.phone)}</a></div>` : '';
  return `<div class="contact-card"><strong>Contact ${esc(name)} to arrange the hand-over</strong>
    <div class="mt-1">${email}${phone}</div></div>`;
}

function claimSection(item) {
  const lost = item.type === 'lost';
  if (item.is_owner) {
    return `<div class="alert alert-info mb-0"><strong>This is your report.</strong>
      <div class="mt-2 d-flex flex-wrap gap-2">
        ${item.status === 'open' ? `<a class="btn btn-sm btn-outline-primary" href="/report?edit=${item.id}">Edit report</a>` : ''}
        <a class="btn btn-sm btn-primary" href="/dashboard">Review claims on your dashboard</a>
      </div></div>`;
  }
  if (item.my_claim) {
    const claim = item.my_claim;
    const note = {
      pending: 'Your claim has been sent. You will be able to see the contact details here once the reporter approves it.',
      approved: 'Your claim was approved.',
      rejected: 'Your claim was not accepted.',
    }[claim.status];
    return `<div class="claim-box"><div class="d-flex justify-content-between align-items-center mb-2">
        <h4 class="h6 m-0">Your claim</h4>${statusPill(claim.status)}</div>
      <p class="mb-2">${esc(note)}</p>
      <blockquote class="small text-muted border-start border-3 ps-3 mb-${claim.status === 'approved' ? '3' : '0'} pre-line">${esc(claim.message)}</blockquote>
      ${claim.status === 'approved' && item.contact ? contactCard(item.reporter_name, item.contact) : ''}</div>`;
  }
  if (item.status !== 'open') {
    return '<div class="alert alert-secondary mb-0">This item has already been returned to its owner.</div>';
  }
  if (!loggedIn) {
    const next = encodeURIComponent(`/browse?item=${item.id}`);
    return `<div class="claim-box"><h4 class="h6">${lost ? 'Did you find this?' : 'Is this yours?'}</h4>
      <p class="mb-3">Log in to send a claim. Contact details are shared only after the reporter approves it.</p>
      <a class="btn btn-primary" href="/login?next=${next}">Log in to send a claim</a>
      <a class="btn btn-outline-primary" href="/register">Create account</a></div>`;
  }
  return `<form class="claim-box" id="claimForm" novalidate>
      <h4 class="h6">${lost ? 'Did you find this?' : 'Is this yours?'}</h4>
      <p class="small text-muted">${lost
        ? 'Tell the owner where you found it and how to reach you after they approve.'
        : 'Describe something only the owner would know, such as marks, contents or a lock-screen detail.'}</p>
      <div class="alert alert-danger d-none" id="claimAlert" role="alert"></div>
      <label class="form-label" for="message">${lost ? 'Your message to the owner' : 'How can you prove it is yours?'}</label>
      <textarea class="form-control" id="message" name="message" rows="3" required minlength="10" maxlength="500" aria-describedby="message-error"></textarea>
      <div class="invalid-feedback" id="message-error"></div>
      <button class="btn btn-primary mt-3" type="submit">Send claim</button>
    </form>`;
}

function renderItem(item) {
  const lost = item.type === 'lost';
  modalHead.className = `modal-header tag-head ${lost ? 'lost' : 'found'}`;
  $('#itemModalTitle').textContent = `${lost ? 'Lost' : 'Found'}: ${item.title}`;
  $('#itemModalNo').textContent = tagNo(item.id);

  const photo = item.image_url
    ? `<img src="${esc(item.image_url)}" alt="Photo of ${esc(item.title)}">`
    : categoryIcon(item.category);
  modalBody.innerHTML = `
    <div class="row g-4">
      <div class="col-md-6"><div class="detail-photo">${photo}</div></div>
      <div class="col-md-6">
        <div class="d-flex align-items-start justify-content-between gap-2">
          <h3 class="h4 mb-2">${esc(item.title)}</h3>${statusPill(item.status)}
        </div>
        <ul class="fact-list">
          <li>${icon('pin')}<div><span class="label">${lost ? 'Lost at' : 'Found at'}</span>${esc(item.location)}</div></li>
          <li>${icon('calendar')}<div><span class="label">Date</span>${formatDate(item.event_date)}</div></li>
          <li>${icon('tag')}<div><span class="label">Category</span>${esc(item.category)}</div></li>
          <li>${icon('user')}<div><span class="label">Reported by</span>${esc(item.reporter_name)}, ${timeAgo(item.created_at)}</div></li>
        </ul>
      </div>
    </div>
    <h4 class="h6 mt-4">Description</h4>
    <p class="pre-line">${esc(item.description)}</p>
    <div class="mt-4">${claimSection(item)}</div>`;

  const claimForm = $('#claimForm', modalBody);
  if (claimForm) claimForm.addEventListener('submit', (event) => submitClaim(event, item));
}

async function submitClaim(event, item) {
  event.preventDefault();
  const claimForm = event.currentTarget;
  const alertBox = $('#claimAlert', claimForm);
  hideAlert(alertBox);
  if (!validateForm(claimForm)) return;                     // client-side validation

  const button = $('button[type="submit"]', claimForm);
  button.disabled = true;
  const { ok, status, data } = await api(`/api/items/${item.id}/claims`, {
    method: 'POST',
    json: { message: claimForm.elements.message.value },
  });
  button.disabled = false;

  if (ok) {
    toast('Claim sent. The reporter has been notified on their dashboard.');
    await refreshItem(item.id);
  } else if (status === 422 && data.errors) {                // server-side validation
    showServerErrors(claimForm, data.errors);
  } else if (status === 401) {
    window.location.href = `/login?next=${encodeURIComponent(`/browse?item=${item.id}`)}`;
  } else {
    showAlert(alertBox, data.error || 'Could not send the claim.');
    if (status === 409) await refreshItem(item.id);
  }
}

modalBody.addEventListener('input', (event) => {
  if (event.target.name === 'message' && event.target.classList.contains('is-invalid')) {
    setFieldError(event.target.form, 'message', '');
  }
});

// ------------------------------------------------------------ start
restoreFromUrl();
load();
const deepLink = new URLSearchParams(window.location.search).get('item');
if (deepLink && /^\d+$/.test(deepLink)) openItem(deepLink);
