// Runs on every page: wires up the Log out button in the common navigation bar.
import { api, toast } from './common.js';

document.querySelectorAll('[data-action="logout"]').forEach((button) => {
  button.addEventListener('click', async () => {
    const { ok } = await api('/api/auth/logout', { method: 'POST' });
    if (ok) {
      window.location.href = '/';
    } else {
      toast('Could not log out. Please try again.', 'danger');
    }
  });
});
