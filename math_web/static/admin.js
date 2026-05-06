'use strict';

// ── DOM ──────────────────────────────────────────────────────────────
const dropZone    = document.getElementById('drop-zone');
const fileInput   = document.getElementById('file-input');
const cropperWrap = document.getElementById('cropper-wrap');
const cropImg     = document.getElementById('crop-img');
const btnCrop     = document.getElementById('btn-crop');
const btnReset    = document.getElementById('btn-reset-crop');
const previewWrap = document.getElementById('preview-wrap');
const previewImg  = document.getElementById('preview-img');
const btnSave     = document.getElementById('btn-save');
const saveMsg     = document.getElementById('save-msg');
const recentList  = document.getElementById('recent-list');

let cropper    = null;
let croppedBlob = null;  // 확정된 크롭 이미지

// ── 파일 선택 ─────────────────────────────────────────────────────────
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('border-accent'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-accent'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('border-accent');
  if (e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) loadFile(fileInput.files[0]); });

function loadFile(file) {
  croppedBlob = null;
  previewWrap.classList.add('hidden');
  cropperWrap.classList.remove('hidden');

  const reader = new FileReader();
  reader.onload = e => {
    cropImg.src = e.target.result;
    if (cropper) { cropper.destroy(); cropper = null; }
    cropper = new Cropper(cropImg, {
      viewMode: 1,
      dragMode: 'crop',
      autoCropArea: 0.8,
      movable: true,
      zoomable: true,
      responsive: true,
    });
  };
  reader.readAsDataURL(file);
}

// ── 크롭 확정 ─────────────────────────────────────────────────────────
btnCrop.addEventListener('click', () => {
  if (!cropper) return;
  const canvas = cropper.getCroppedCanvas({ maxWidth: 1600, maxHeight: 1200 });
  canvas.toBlob(blob => {
    croppedBlob = blob;
    previewImg.src = URL.createObjectURL(blob);
    previewWrap.classList.remove('hidden');
    cropperWrap.classList.add('hidden');
  }, 'image/png');
});

btnReset.addEventListener('click', () => {
  croppedBlob = null;
  previewWrap.classList.add('hidden');
  cropperWrap.classList.remove('hidden');
  if (cropper) cropper.reset();
});

// ── 저장 ─────────────────────────────────────────────────────────────
btnSave.addEventListener('click', async () => {
  const authRes = await fetch('/auth/me');
  if (!authRes.ok) {
    location.href = '/static/login.html?next=' + encodeURIComponent(location.pathname);
    return;
  }

  const year     = document.getElementById('f-year').value;
  const examType = document.getElementById('f-exam-type').value;
  const number   = document.getElementById('f-number').value;

  if (!croppedBlob)  { flash('이미지를 크롭해 주세요', 'error'); return; }
  if (!year)         { flash('연도를 입력해 주세요', 'error'); return; }
  if (!examType)     { flash('시험 유형을 선택해 주세요', 'error'); return; }
  if (!number)       { flash('번호를 입력해 주세요', 'error'); return; }

  btnSave.disabled = true;
  const form = new FormData();
  form.append('image',      croppedBlob, 'problem.png');
  form.append('year',       year);
  form.append('exam_type',  examType);
  form.append('number',     number);
  form.append('score',      document.getElementById('f-score').value || '3');
  form.append('answer',     document.getElementById('f-answer').value);
  form.append('unit',       document.getElementById('f-unit').value);
  form.append('difficulty', document.getElementById('f-difficulty').value);
  form.append('has_figure', document.getElementById('f-has-figure').checked ? 'true' : 'false');
  form.append('text',       document.getElementById('f-text').value);
  form.append('latex',      document.getElementById('f-latex').value);
  form.append('notes',      document.getElementById('f-notes').value);

  try {
    const res = await fetch('/db/problems', { method: 'POST', body: form });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }
    flash('저장 완료!', 'ok');
    resetForm();
    loadRecent();
    // 번호 자동 증가
    const numEl = document.getElementById('f-number');
    if (numEl.value) numEl.value = parseInt(numEl.value) + 1;
  } catch (e) {
    flash('오류: ' + e.message, 'error');
  } finally {
    btnSave.disabled = false;
  }
});

function resetForm() {
  croppedBlob = null;
  previewWrap.classList.add('hidden');
  cropperWrap.classList.add('hidden');
  if (cropper) { cropper.destroy(); cropper = null; }
  cropImg.src = '';
  // 이미지 관련 외 입력값 유지 (연도/시험/단원 등은 연속 입력 편의상)
  document.getElementById('f-answer').value = '';
  document.getElementById('f-text').value   = '';
  document.getElementById('f-latex').value  = '';
  document.getElementById('f-notes').value  = '';
  document.getElementById('f-has-figure').checked = false;
}

// ── 최근 저장 목록 ────────────────────────────────────────────────────
async function loadRecent() {
  try {
    const res  = await fetch('/db/problems?limit=8&offset=0');
    const data = await res.json();
    recentList.innerHTML = '';
    data.problems.forEach(p => {
      const card = document.createElement('div');
      card.className = 'border border-border rounded-xl bg-white overflow-hidden cursor-pointer hover:border-accent transition-colors group relative';
      card.innerHTML = `
        <img src="${p.image_path}" alt="" class="w-full object-contain bg-gray-50" style="max-height:120px"/>
        <div class="px-3 py-2 text-xs text-gray-600 space-y-0.5">
          <div class="font-medium">${p.year} ${p.exam_type} ${p.number}번</div>
          <div class="text-gray-400">${p.unit || '단원미정'} · ${p.difficulty || '난이도미정'}</div>
        </div>
        <button class="btn-del absolute top-1 right-1 w-6 h-6 rounded-full bg-white/80 text-gray-400
                       hover:text-red-500 hidden group-hover:flex items-center justify-center text-xs border border-border"
                data-id="${p.id}">✕</button>
      `;
      card.querySelector('.btn-del').addEventListener('click', async e => {
        e.stopPropagation();
        if (!confirm('삭제하시겠습니까?')) return;
        await fetch(`/db/problems/${p.id}`, { method: 'DELETE' });
        loadRecent();
      });
      recentList.appendChild(card);
    });
  } catch (_) {}
}

function flash(msg, type) {
  saveMsg.textContent = msg;
  saveMsg.className = `text-sm text-center py-1.5 rounded-lg ${type === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`;
  saveMsg.classList.remove('hidden');
  setTimeout(() => saveMsg.classList.add('hidden'), 3000);
}

// 초기 로드
loadRecent();
