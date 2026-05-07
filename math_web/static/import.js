'use strict';

const phaseUpload = document.getElementById('phase-upload');
const phaseReview = document.getElementById('phase-review');
const phaseDone   = document.getElementById('phase-done');

const fileInput     = document.getElementById('file-input');
const dropZone      = document.getElementById('drop-zone');
const fileNameDiv   = document.getElementById('file-name');
const btnAnalyze    = document.getElementById('btn-analyze');
const analyzeProgress = document.getElementById('analyze-progress');
const progressText  = document.getElementById('progress-text');

const totalCountEl  = document.getElementById('total-count');
const reviewList    = document.getElementById('review-list');
const btnBack       = document.getElementById('btn-back');
const bulkUnit      = document.getElementById('bulk-unit');
const bulkDiff      = document.getElementById('bulk-diff');
const btnBulkApply  = document.getElementById('btn-bulk-apply');
const chkSelectAll  = document.getElementById('chk-select-all');
const btnSaveAll    = document.getElementById('btn-save-all');
const btnSaveAllBot = document.getElementById('btn-save-all-bottom');

const savedCountEl  = document.getElementById('saved-count');
const btnImportMore = document.getElementById('btn-import-more');

let problems = [];

// ── File selection ────────────────────────────────────────────────
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('border-accent', 'bg-amber-50'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-accent', 'bg-amber-50'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('border-accent', 'bg-amber-50');
  const f = e.dataTransfer.files[0];
  if (f) setFile(f);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

function setFile(f) {
  fileNameDiv.textContent = f.name;
  fileNameDiv.classList.remove('hidden');
}

// ── Phase 1 → analyze ────────────────────────────────────────────
btnAnalyze.addEventListener('click', async () => {
  const year = document.getElementById('f-year').value.trim();
  const examType = document.getElementById('f-exam-type').value;
  const file = fileInput.files[0];

  if (!year || !examType) return alert('연도와 시험을 선택해 주세요.');
  if (!file) return alert('PDF 파일을 선택해 주세요.');

  const fd = new FormData();
  fd.append('pdf', file);
  fd.append('year', year);
  fd.append('exam_type', examType);

  btnAnalyze.disabled = true;
  analyzeProgress.classList.remove('hidden');

  let pagesDone = 0;
  const timer = setInterval(() => {
    pagesDone++;
    progressText.textContent = `분석 중... (약 ${pagesDone * 15}초 경과)`;
  }, 15000);

  try {
    const res = await fetch('/db/import-pdf', { method: 'POST', body: fd });
    clearInterval(timer);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    problems = data.problems;
    renderReview();
  } catch (e) {
    clearInterval(timer);
    alert('분석 실패: ' + e.message);
  } finally {
    btnAnalyze.disabled = false;
    analyzeProgress.classList.add('hidden');
  }
});

// ── Phase 2: render review list ──────────────────────────────────
const UNITS = ['대수', '미적분1', '미적분2', '확률과통계', '기하'];
const DIFFS = ['상', '중', '하'];

function renderReview() {
  phaseUpload.classList.add('hidden');
  phaseReview.classList.remove('hidden');
  totalCountEl.textContent = problems.length;
  reviewList.innerHTML = '';

  problems.forEach((p, i) => {
    const card = document.createElement('div');
    card.className = 'bg-white border border-border rounded-xl p-4 flex gap-4 items-start';
    card.dataset.index = i;

    card.innerHTML = `
      <input type="checkbox" class="chk-item mt-1 accent-amber-600 w-4 h-4 shrink-0" data-index="${i}" />
      <img src="${p.image_path}" alt="문제 ${p.number}"
           class="w-40 shrink-0 rounded border border-border object-contain bg-gray-50" />
      <div class="flex-1 min-w-0 space-y-2">
        <div class="flex items-center gap-3 flex-wrap">
          <span class="text-xs font-semibold text-gray-500">${p.number}번</span>
          <select class="sel-unit border border-border rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40">
            <option value="">단원 선택</option>
            ${UNITS.map(u => `<option value="${u}"${p.unit === u ? ' selected' : ''}>${u}</option>`).join('')}
          </select>
          <select class="sel-diff border border-border rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40">
            <option value="">난이도</option>
            ${DIFFS.map(d => `<option value="${d}"${p.difficulty === d ? ' selected' : ''}>${d}</option>`).join('')}
          </select>
          <label class="text-xs text-gray-500 flex items-center gap-1">
            배점
            <input type="number" class="inp-score w-12 border border-border rounded px-1.5 py-1 text-sm" min="1" max="10" value="${p.score || 3}" />
          </label>
          <label class="text-xs text-gray-500 flex items-center gap-1">
            정답
            <input type="text" class="inp-answer w-16 border border-border rounded px-1.5 py-1 text-sm" value="${p.answer || ''}" placeholder="없음" />
          </label>
        </div>
        <p class="text-xs text-gray-500 leading-relaxed line-clamp-3">${p.text || '(텍스트 없음)'}</p>
      </div>
    `;

    // wire up change events
    card.querySelector('.sel-unit').addEventListener('change', e => { problems[i].unit = e.target.value; });
    card.querySelector('.sel-diff').addEventListener('change', e => { problems[i].difficulty = e.target.value; });
    card.querySelector('.inp-score').addEventListener('change', e => { problems[i].score = parseInt(e.target.value) || 3; });
    card.querySelector('.inp-answer').addEventListener('change', e => { problems[i].answer = e.target.value; });

    reviewList.appendChild(card);
  });
}

// ── Select all ───────────────────────────────────────────────────
chkSelectAll.addEventListener('change', () => {
  document.querySelectorAll('.chk-item').forEach(c => { c.checked = chkSelectAll.checked; });
});

// ── Bulk apply ───────────────────────────────────────────────────
btnBulkApply.addEventListener('click', () => {
  const unit = bulkUnit.value;
  const diff = bulkDiff.value;
  if (!unit && !diff) return alert('단원 또는 난이도를 선택해 주세요.');

  document.querySelectorAll('.chk-item:checked').forEach(chk => {
    const i = parseInt(chk.dataset.index);
    const card = reviewList.querySelector(`[data-index="${i}"]`);
    if (unit) {
      problems[i].unit = unit;
      card.querySelector('.sel-unit').value = unit;
    }
    if (diff) {
      problems[i].difficulty = diff;
      card.querySelector('.sel-diff').value = diff;
    }
  });
});

// ── Back ─────────────────────────────────────────────────────────
btnBack.addEventListener('click', () => {
  phaseReview.classList.add('hidden');
  phaseUpload.classList.remove('hidden');
  problems = [];
});

// ── Save ─────────────────────────────────────────────────────────
async function saveAll() {
  const btn = btnSaveAll;
  btn.disabled = true;
  btn.textContent = '저장 중...';

  try {
    const res = await fetch('/db/import-pdf/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(problems),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    savedCountEl.textContent = data.saved;
    phaseReview.classList.add('hidden');
    phaseDone.classList.remove('hidden');
  } catch (e) {
    alert('저장 실패: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '전체 저장';
  }
}

btnSaveAll.addEventListener('click', saveAll);
btnSaveAllBot.addEventListener('click', saveAll);

// ── Import more ──────────────────────────────────────────────────
btnImportMore.addEventListener('click', () => {
  phaseDone.classList.add('hidden');
  phaseUpload.classList.remove('hidden');
  fileInput.value = '';
  fileNameDiv.classList.add('hidden');
  fileNameDiv.textContent = '';
  problems = [];
});
