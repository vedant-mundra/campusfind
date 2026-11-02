// MODULE 1 (Student 1): register and login pages.
import { $, api, hideAlert, setBusy, setFieldError, showAlert, showServerErrors, validateForm } from './common.js';

// "Show / Hide" button next to password fields
document.querySelectorAll('[data-toggle-password]').forEach((button) => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.togglePassword);
    const reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    button.textContent = reveal ? 'Hide' : 'Show';
    button.setAttribute('aria-pressed', String(reveal));
  });
});

/** Only follow same-site relative paths after login. */
const safeNext = (url) => (url && url.startsWith('/') && !url.startsWith('//') ? url : '/dashboard');

// ------------------------------------------------------------ registration
function initRegister(form) {
  const password = $('#password', form);
  const confirm = $('#confirm_password', form);
  const alertBox = $('#formAlert', form);

  const rules = {
    length: (v) => v.length >= 8,
    letter: (v) => /[A-Za-z]/.test(v),
    digit: (v) => /\d/.test(v),
  };

  // Live checklist + custom validity rules (these feed the Constraint Validation API)
  function checkPasswords() {
    let allOk = true;
    for (const [name, test] of Object.entries(rules)) {
      const ok = test(password.value);
      $(`[data-rule="${name}"]`, form).classList.toggle('ok', ok);
      allOk = allOk && ok;
    }
    password.setCustomValidity(allOk ? '' : 'Password must be 8+ characters with a letter and a number.');
    confirm.setCustomValidity(confirm.value === password.value ? '' : 'The two passwords do not match.');
  }
  password.addEventListener('input', checkPasswords);
  confirm.addEventListener('input', checkPasswords);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    hideAlert(alertBox);
    checkPasswords();
    if (!validateForm(form)) return;                      // client-side validation

    const button = $('#submitBtn', form);
    setBusy(button, true, 'Creating account…');
    const { ok, status, data } = await api('/api/auth/register', {
      method: 'POST',
      json: Object.fromEntries(new FormData(form)),       // sent as JSON
    });
    if (ok) {
      window.location.href = '/dashboard';
      return;
    }
    setBusy(button, false);
    if (status === 422 && data.errors) {                  // server-side validation messages
      if (!showServerErrors(form, data.errors)) showAlert(alertBox, data.error);
    } else {
      showAlert(alertBox, data.error || 'Registration failed. Please try again.');
    }
  });

  form.addEventListener('input', (e) => e.target.name && e.target.classList.contains('is-invalid') && clearFieldOnInput(form, e.target));
}

// ------------------------------------------------------------ login
function initLogin(form) {
  const alertBox = $('#formAlert', form);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    hideAlert(alertBox);
    if (!validateForm(form)) return;

    const button = $('#submitBtn', form);
    setBusy(button, true, 'Logging in…');
    const { ok, status, data } = await api('/api/auth/login', {
      method: 'POST',
      json: Object.fromEntries(new FormData(form)),
    });
    if (ok) {
      window.location.href = safeNext(form.dataset.next);
      return;
    }
    setBusy(button, false);
    if (status === 422 && data.errors) showServerErrors(form, data.errors);
    else showAlert(alertBox, data.error || 'Login failed. Please try again.');
    $('#password', form).value = '';
    $('#password', form).focus();
  });

  form.addEventListener('input', (e) => e.target.name && e.target.classList.contains('is-invalid') && clearFieldOnInput(form, e.target));
}

/** Remove a field's error as soon as the user starts correcting it. */
function clearFieldOnInput(form, field) {
  setFieldError(form, field.name, '');
}

const registerForm = $('#registerForm');
const loginForm = $('#loginForm');
if (registerForm) initRegister(registerForm);
if (loginForm) initLogin(loginForm);
