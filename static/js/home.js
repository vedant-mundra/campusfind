// Home page: live numbers, the newest report on the hero tag, and a "recently reported" grid.
import { api, emptyState, itemCard } from './common.js';

async function loadStats() {
  const { ok, data } = await api('/api/stats');
  if (!ok) return;
  document.querySelectorAll('[data-stat]').forEach((el) => {
    el.textContent = data[el.dataset.stat] ?? '–';
  });
}

async function loadRecent() {
  const grid = document.getElementById('recentGrid');
  const { ok, data } = await api('/api/items?per_page=5');
  if (!ok) {
    grid.innerHTML = '<p class="col-12 text-muted">Recent reports could not be loaded right now.</p>';
    return;
  }
  const [newest, ...others] = data.items;

  if (newest) {   // the hero tag shows the newest real report
    document.getElementById('heroTag').innerHTML = itemCard(newest, { href: `/browse?item=${newest.id}` });
  } else {
    document.getElementById('heroTagCaption').textContent = 'Be the first to post a report';
  }

  grid.innerHTML = others.length
    ? others.map((item) => `<div class="col-sm-6 col-lg-3">${itemCard(item, { href: `/browse?item=${item.id}` })}</div>`).join('')
    : emptyState('No other reports yet', 'New reports will show up here.');
  grid.removeAttribute('aria-busy');
}

loadStats();
loadRecent();
