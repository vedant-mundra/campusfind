// MODULE 4 (Student 2): dashboard - stats, my reports, claims received (approve/decline), my claims.
import {
  $, $$, api, categoryIcon, confirmDialog, emptyState, esc, formatDate, hideAlert, icon,
  showAlert, statusPill, timeAgo, toast,
} from './common.js';

const pageAlert = $('#pageAlert');

async function loadAll() {
  const responses = await Promise.all([
    api('/api/me/stats'), api('/api/me/items'), api('/api/me/claims/received'), api('/api/me/claims'),
  ]);
  if (responses.some((r) => r.status === 401)) {
    window.location.href = '/login?next=/dashboard';
    return;
  }
  const failed = responses.find((r) => !r.ok);
  if (failed) {
    showAlert(pageAlert, failed.data.error || 'Your dashboard could not be loaded.');
    return;
  }
  hideAlert(pageAlert);
  const [stats, items, received, sent] = responses.map((r) => r.data);
  renderStats(stats);
  renderReports(items.items);
  renderReceived(received.claims);
  renderSent(sent.claims);
}

// ------------------------------------------------------------ stats
function renderStats(stats) {
  $$('[data-stat]').forEach((el) => { el.textContent = stats[el.dataset.stat] ?? 0; });
  $('#pendingCard').classList.toggle('attn', stats.pending_received > 0);
  const badge = $('#receivedBadge');
  badge.textContent = stats.pending_received;
  badge.classList.toggle('d-none', stats.pending_received === 0);
  badge.setAttribute('aria-label', `${stats.pending_received} waiting`);
}

// ------------------------------------------------------------ tab 1: my reports
function renderReports(items) {
  const pane = $('#pane-reports');
  if (!items.length) {
    pane.innerHTML = `<div class="row">${emptyState(
      'You have not reported anything yet',
      'Lost something, or found something that is not yours? Post a report so it can find its way home.',
      '<a class="btn btn-accent" href="/report">Report an item</a>',
    )}</div>`;
    return;
  }
  const rows = items.map((item) => {
    const open = item.status === 'open';
    const thumb = item.image_url
      ? `<img class="thumb" src="${esc(item.image_url)}" alt="">`
      : `<span class="thumb">${categoryIcon(item.category)}</span>`;
    return `<tr>
      <td><div class="d-flex align-items-center gap-3">${thumb}
        <div><a class="fw-semibold" href="/browse?item=${item.id}">${esc(item.title)}</a>
        <div class="small text-muted">${esc(item.category)}, ${esc(item.location)}</div></div></div></td>
      <td><span class="pill pill-${item.type}">${item.type === 'lost' ? 'Lost' : 'Found'}</span></td>
      <td>${statusPill(item.status)}</td>
      <td>${item.pending_claims > 0 ? `<span class="pill pill-pending">${item.pending_claims} pending</span>` : '<span class="text-muted">None</span>'}</td>
      <td class="text-nowrap">${formatDate(item.created_at.slice(0, 10))}</td>
      <td class="text-end text-nowrap">
        ${open ? `<a class="btn btn-sm btn-outline-primary" href="/report?edit=${item.id}" aria-label="Edit ${esc(item.title)}">Edit</a>
        <button class="btn btn-sm btn-outline-primary" type="button" data-act="resolve" data-id="${item.id}" data-title="${esc(item.title)}">Mark returned</button>` : ''}
        <button class="btn btn-sm btn-outline-danger" type="button" data-act="delete" data-id="${item.id}" data-title="${esc(item.title)}" aria-label="Delete ${esc(item.title)}">Delete</button>
      </td></tr>`;
  }).join('');
  pane.innerHTML = `<div class="panel p-0 overflow-hidden"><div class="table-responsive">
    <table class="table"><caption class="visually-hidden">Your reports</caption>
    <thead><tr><th scope="col">Item</th><th scope="col">Type</th><th scope="col">Status</th>
    <th scope="col">Claims</th><th scope="col">Reported</th><th scope="col"><span class="visually-hidden">Actions</span></th></tr></thead>
    <tbody>${rows}</tbody></table></div></div>`;
}

// ------------------------------------------------------------ tab 2: claims received
function renderReceived(claims) {
  const pane = $('#pane-received');
  if (!claims.length) {
    pane.innerHTML = `<div class="row">${emptyState('No claims yet', 'When someone sends a claim on one of your reports, it will show up here for you to approve or decline.')}</div>`;
    return;
  }
  pane.innerHTML = claims.map((c) => {
    const actions = c.status === 'pending'
      ? `<div class="d-flex flex-wrap gap-2">
          <button class="btn btn-sm btn-success" type="button" data-act="approve" data-id="${c.id}" data-title="${esc(c.item_title)}" data-name="${esc(c.claimant_name)}" aria-label="Approve claim from ${esc(c.claimant_name)} on ${esc(c.item_title)}">Approve</button>
          <button class="btn btn-sm btn-outline-danger" type="button" data-act="reject" data-id="${c.id}" aria-label="Decline claim from ${esc(c.claimant_name)} on ${esc(c.item_title)}">Decline</button>
        </div>`
      : c.status === 'approved' && c.claimant_email
        ? `<div class="contact-card small">${icon('mail', 'me-1')}Contact ${esc(c.claimant_name)}: <a href="mailto:${esc(c.claimant_email)}">${esc(c.claimant_email)}</a></div>`
        : '';
    return `<article class="claim-item">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div><a class="fw-semibold" href="/browse?item=${c.item_id}">${esc(c.item_title)}</a>
          <span class="pill pill-${c.item_type} ms-1">${c.item_type === 'lost' ? 'Lost' : 'Found'}</span></div>
        ${statusPill(c.status)}
      </div>
      <div class="small text-muted mt-1">From <strong>${esc(c.claimant_name)}</strong>, ${timeAgo(c.created_at)}</div>
      <blockquote class="pre-line">${esc(c.message)}</blockquote>
      ${actions}
    </article>`;
  }).join('');
}

// ------------------------------------------------------------ tab 3: claims I sent
function renderSent(claims) {
  const pane = $('#pane-sent');
  if (!claims.length) {
    pane.innerHTML = `<div class="row">${emptyState(
      'You have not sent any claims',
      'Found your item in the list? Open it and send a claim.',
      '<a class="btn btn-primary" href="/browse">Browse items</a>',
    )}</div>`;
    return;
  }
  pane.innerHTML = claims.map((c) => {
    const contact = c.contact
      ? `<div class="contact-card mt-2"><strong>Contact ${esc(c.reporter_name)}</strong>
          <div>${icon('mail', 'me-1')}<a href="mailto:${esc(c.contact.email)}">${esc(c.contact.email)}</a></div>
          ${c.contact.phone ? `<div>${icon('phone', 'me-1')}<a href="tel:${esc(c.contact.phone)}">${esc(c.contact.phone)}</a></div>` : ''}</div>`
      : '';
    const note = { pending: 'Waiting for the reporter to respond.', approved: 'Approved. You can now contact the reporter.', rejected: 'The reporter did not accept this claim.' }[c.status];
    return `<article class="claim-item">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div><a class="fw-semibold" href="/browse?item=${c.item_id}">${esc(c.item_title)}</a>
          <span class="pill pill-${c.item_type} ms-1">${c.item_type === 'lost' ? 'Lost' : 'Found'}</span></div>
        ${statusPill(c.status)}
      </div>
      <div class="small text-muted mt-1">Sent ${timeAgo(c.created_at)}. ${esc(note)}</div>
      <blockquote class="pre-line">${esc(c.message)}</blockquote>${contact}
    </article>`;
  }).join('');
}

// ------------------------------------------------------------ actions (event delegation)
async function run(request, successMessage) {
  const { ok, data } = await request;
  if (ok) {
    toast(successMessage);
    await loadAll();
  } else {
    toast(data.error || 'That did not work. Please try again.', 'danger');
    await loadAll();
  }
}

document.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-act]');
  if (!button) return;
  const { act, id, title, name } = button.dataset;

  if (act === 'approve') {
    const yes = await confirmDialog({
      title: `Approve ${name}'s claim?`,
      text: `"${title}" will be marked as returned, other pending claims will be declined, and ${name} will see your email and phone number.`,
      okLabel: 'Approve claim', okClass: 'btn-success',
    });
    if (yes) run(api(`/api/claims/${id}/decision`, { method: 'POST', json: { decision: 'approved' } }), 'Claim approved. The item is marked as returned.');
  } else if (act === 'reject') {
    run(api(`/api/claims/${id}/decision`, { method: 'POST', json: { decision: 'rejected' } }), 'Claim declined.');
  } else if (act === 'resolve') {
    const yes = await confirmDialog({
      title: 'Mark as returned?',
      text: `"${title}" will be closed and any pending claims will be declined.`,
      okLabel: 'Mark returned', okClass: 'btn-primary',
    });
    if (yes) run(api(`/api/items/${id}/resolve`, { method: 'POST' }), 'Marked as returned.');
  } else if (act === 'delete') {
    const yes = await confirmDialog({
      title: 'Delete this report?',
      text: `"${title}", its photo and all claims on it will be removed permanently.`,
      okLabel: 'Delete report', okClass: 'btn-danger',
    });
    if (yes) run(api(`/api/items/${id}`, { method: 'DELETE' }), 'Report deleted.');
  }
});

loadAll();
