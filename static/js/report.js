// MODULE 2 (Student 1): report a lost/found item, edit it, delete it.
import {
  $, api, confirmDialog, hideAlert, setBusy, setFieldError, showAlert,
  showServerErrors, tagNo, todayIso, validateForm,
} from './common.js';

const form = $('#reportForm');
const formAlert = $('#formAlert');
const pageAlert = $('#pageAlert');
const params = new URLSearchParams(window.location.search);
const editId = params.get('edit');                 // /report?edit=12 -> edit mode
const MAX_PHOTO_BYTES = 3 * 1024 * 1024;

const WORDING = {
  lost: { date: 'Date you lost it', where: 'Where did you lose it?', title: 'e.g. Black umbrella with wooden handle' },
  found: { date: 'Date you found it', where: 'Where did you find it?', title: 'e.g. Calculator with a blue cover' },
};

// ---- date limits: not in the future, not more than a year ago (mirrors the server rule)
const dateInput = $('#event_date');
const yearAgo = new Date();
yearAgo.setFullYear(yearAgo.getFullYear() - 1);
dateInput.max = todayIso();
dateInput.min = `${yearAgo.getFullYear()}-${String(yearAgo.getMonth() + 1).padStart(2, '0')}-${String(yearAgo.getDate()).padStart(2, '0')}`;

// ---- wording changes with the selected type
function applyType(type) {
  const words = WORDING[type];
  if (!words) return;
  $('#dateLabel').textContent = words.date;
  $('#locationLabel').textContent = words.where;
  $('#title').placeholder = words.title;
}
form.addEventListener('change', (event) => {
  if (event.target.name === 'type') {
    applyType(event.target.value);
    setFieldError(form, 'type', '');
  }
});

// ---- live character counter
const description = $('#description');
const counter = $('#descCount');
const updateCounter = () => { counter.textContent = `${description.value.length} / 500`; };
description.addEventListener('input', updateCounter);

// ---- clear a field's error as soon as the user edits it
form.addEventListener('input', (event) => {
  if (event.target.name && event.target.classList.contains('is-invalid')) setFieldError(form, event.target.name, '');
});

// ---- photo: client-side type/size check and preview
const photoInput = $('#photo');
const previewBox = $('#photoPreviewBox');
const preview = $('#photoPreview');
function showPreview(src) { preview.src = src; previewBox.classList.remove('d-none'); }
function hidePreview() { preview.removeAttribute('src'); previewBox.classList.add('d-none'); }

photoInput.addEventListener('change', () => {
  setFieldError(form, 'photo', '');
  const file = photoInput.files[0];
  if (!file) { hidePreview(); return; }
  let problem = '';
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) problem = 'Photo must be a JPG, PNG or WEBP image.';
  else if (file.size > MAX_PHOTO_BYTES) problem = 'Photo must be 3 MB or smaller.';
  if (problem) {
    photoInput.value = '';
    hidePreview();
    setFieldError(form, 'photo', problem);
    return;
  }
  showPreview(URL.createObjectURL(file));
});

// ---- submit: POST /api/items (create) or PUT /api/items/<id> (edit), as multipart/form-data
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  hideAlert(formAlert);
  if (!validateForm(form)) return;                        // client-side validation

  const body = new FormData(form);                        // text fields + the photo file
  if (editId && $('#removePhoto').checked) body.append('remove_photo', '1');

  const button = $('#submitBtn');
  setBusy(button, true, 'Saving…');
  const { ok, status, data } = await api(editId ? `/api/items/${editId}` : '/api/items', {
    method: editId ? 'PUT' : 'POST',
    form: body,
  });
  setBusy(button, false);

  if (ok) {
    showSuccess(data.item);
  } else if ((status === 422 || status === 413) && data.errors) {   // server-side validation
    if (!showServerErrors(form, data.errors)) showAlert(formAlert, data.error);
  } else if (status === 401) {
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
  } else {
    showAlert(formAlert, data.error || 'Could not save the report. Please try again.');
  }
});

function showSuccess(item) {
  form.classList.add('d-none');
  hideAlert(pageAlert);
  const panel = $('#successPanel');
  $('#successTag').textContent = tagNo(item.id);
  $('#successTitle').textContent = editId ? 'Changes saved' : 'Your report is live';
  $('#successText').textContent = editId
    ? 'Your report has been updated.'
    : 'People can now find it by searching. When someone sends a claim you will see it on your dashboard.';
  $('#successView').href = `/browse?item=${item.id}`;
  $('#successAnother').classList.toggle('d-none', Boolean(editId));
  panel.classList.remove('d-none');
  panel.focus();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---- edit mode: load the existing report into the form
async function loadForEdit() {
  $('#pageTitle').textContent = 'Edit your report';
  $('#pageIntro').textContent = 'Update the details, replace the photo or delete the report.';
  $('#submitBtn').textContent = 'Save changes';
  document.title = 'Edit report - CampusFind';

  const { ok, data } = await api(`/api/items/${editId}`);
  const item = data.item;
  const blocked = !ok ? (data.error || 'This report could not be loaded.')
    : !item.is_owner ? 'You can only edit your own reports.'
    : item.status === 'resolved' ? 'This report is already resolved and can no longer be edited.' : '';
  if (blocked) {
    form.classList.add('d-none');
    showAlert(pageAlert, blocked);
    return;
  }

  form.elements.namedItem('type').value = item.type;
  applyType(item.type);
  $('#title').value = item.title;
  $('#category').value = item.category;
  dateInput.value = item.event_date;
  $('#location').value = item.location;
  description.value = item.description;
  updateCounter();
  $('#phone').value = item.contact?.phone || '';
  if (item.image_url) {
    showPreview(item.image_url);
    $('#removePhotoRow').classList.remove('d-none');
  }
  $('#deleteBtn').classList.remove('d-none');
}

$('#deleteBtn').addEventListener('click', async () => {
  const confirmed = await confirmDialog({
    title: 'Delete this report?',
    text: 'This removes the report, its photo and any claims people have sent. It cannot be undone.',
    okLabel: 'Delete report',
    okClass: 'btn-danger',
  });
  if (!confirmed) return;
  const { ok, data } = await api(`/api/items/${editId}`, { method: 'DELETE' });
  if (ok) window.location.href = '/dashboard';
  else showAlert(formAlert, data.error || 'Could not delete the report.');
});

// ---- start
if (editId) {
  loadForEdit();
} else {
  dateInput.value = todayIso();
  const preset = params.get('type');
  if (preset === 'lost' || preset === 'found') {
    form.elements.namedItem('type').value = preset;
    applyType(preset);
  }
}
