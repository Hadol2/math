'use strict';

// ── 상태 ─────────────────────────────────────────────────────────────
let allProblems  = [];   // 현재 페이지 문제 목록
let selected     = new Map();  // id → problem object
let currentPage  = 0;
let totalCount   = 0;
const PAGE_SIZE  = 40;

// ── DOM ──────────────────────────────────────────────────────────────
const fYear     = document.getElementById('f-year');
const fExam     = document.getElementById('f-exam');
const fUnit     = document.getElementById('f-unit');
const fDiff     = document.getElementById('f-diff');
const btnSearch = document.getElementById('btn-search');
const btnClear  = document.getElementById('btn-clear');
const probGrid  = document.getElementById('prob-grid');
const resCount  = document.getElementById('result-count');
const emptyState = document.getElementById('empty-state');
const pagination = document.getElementById('pagination');
const selCount  = document.getElementById('sel-count');
const selNum    = document.getElementById('sel-num');
const btnCompose = document.getElementById('btn-compose');
const btnSelAll  = document.getElementById('btn-sel-all');
const btnSelNone = document.getElementById('btn-sel-none');

// 모달
const composeModal = document.getElementById('compose-modal');
const modalClose   = document.getElementById('modal-close');
const modalBackdrop = document.getElementById('modal-backdrop');
const modalCount   = document.getElementById('modal-count');
const composeList  = document.getElementById('compose-list');
const btnGenPdf    = document.getElementById('btn-gen-pdf');
const pdfSpinner   = document.getElementById('pdf-spinner');
const chkAnswers   = document.getElementById('chk-answers');

// ── 연도 드롭다운 채우기 ──────────────────────────────────────────────
(function populateYears() {
  const curYear = new Date().getFullYear();
  for (let y = curYear; y >= 1994; y--) {
    const opt = document.createElement('option');
    opt.value = y; opt.textContent = y + '학년도';
    fYear.appendChild(opt);
  }
})();

// ── 검색 ─────────────────────────────────────────────────────────────
async function search(page = 0) {
  currentPage = page;
  const params = new URLSearchParams({ limit: PAGE_SIZE, offset: page * PAGE_SIZE });
  if (fYear.value)  params.set('year',       fYear.value);
  if (fExam.value)  params.set('exam_type',  fExam.value);
  if (fUnit.value)  params.set('unit',       fUnit.value);
  if (fDiff.value)  params.set('difficulty', fDiff.value);

  resCount.textContent = '검색 중...';
  probGrid.innerHTML   = '';
  emptyState.classList.add('hidden');

  try {
    const res  = await fetch('/db/problems?' + params);
    const data = await res.json();
    allProblems = data.problems;
    totalCount  = data.total;
    renderGrid();
    renderPagination();
    resCount.textContent = `총 ${totalCount}개 문제`;
    if (allProblems.length === 0) emptyState.classList.remove('hidden');
  } catch (e) {
    resCount.textContent = '오류 발생';
  }
}

function renderGrid() {
  probGrid.innerHTML = '';
  allProblems.forEach(p => {
    const card = document.createElement('div');
    const isSelected = selected.has(p.id);
    card.className = `prob-card border border-border rounded-xl bg-white overflow-hidden cursor-pointer
                      hover:border-accent/60 transition-all relative${isSelected ? ' selected' : ''}`;
    card.dataset.id = p.id;

    const diffColor = { 상: 'text-red-500', 중: 'text-amber-500', 하: 'text-green-600' }[p.difficulty] || 'text-gray-400';
    card.innerHTML = `
      <!-- 체크 배지 -->
      <div class="check-mark absolute top-2 right-2 w-6 h-6 rounded-full bg-accent text-white
                  items-center justify-center text-xs font-bold z-10">✓</div>
      <img src="${p.image_path}" alt="" class="w-full object-contain bg-gray-50" style="max-height:130px" loading="lazy"/>
      <div class="px-2.5 py-2 text-xs space-y-0.5">
        <div class="font-semibold text-gray-700">${p.year} ${p.exam_type} ${p.number}번</div>
        <div class="flex gap-1 text-gray-400">
          <span>${p.unit || '단원미정'}</span>
          ${p.difficulty ? `<span class="font-medium ${diffColor}">· ${p.difficulty}</span>` : ''}
          ${p.has_figure ? '<span class="text-blue-400">· 도형</span>' : ''}
        </div>
        ${p.answer ? `<div class="text-gray-400">정답: <span class="font-medium text-gray-600">${p.answer}</span></div>` : ''}
      </div>
    `;

    card.addEventListener('click', () => toggleSelect(p, card));
    probGrid.appendChild(card);
  });
}

function renderPagination() {
  pagination.innerHTML = '';
  const pages = Math.ceil(totalCount / PAGE_SIZE);
  if (pages <= 1) return;

  const makeBtn = (label, page, disabled = false) => {
    const btn = document.createElement('button');
    btn.textContent = label;
    btn.disabled = disabled;
    btn.className = `px-3 py-1 rounded-lg border text-sm transition-colors
      ${page === currentPage ? 'bg-accent text-white border-accent' : 'border-border hover:bg-gray-100'}
      ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`;
    if (!disabled) btn.addEventListener('click', () => search(page));
    return btn;
  };

  pagination.appendChild(makeBtn('‹', currentPage - 1, currentPage === 0));
  for (let i = 0; i < pages; i++) {
    if (pages > 7 && Math.abs(i - currentPage) > 2 && i !== 0 && i !== pages - 1) {
      if (i === 1 || i === pages - 2) {
        const dots = document.createElement('span');
        dots.textContent = '…'; dots.className = 'px-2 py-1 text-sm text-gray-400';
        pagination.appendChild(dots);
      }
      continue;
    }
    pagination.appendChild(makeBtn(i + 1, i));
  }
  pagination.appendChild(makeBtn('›', currentPage + 1, currentPage >= pages - 1));
}

// ── 선택 토글 ─────────────────────────────────────────────────────────
function toggleSelect(prob, cardEl) {
  if (selected.has(prob.id)) {
    selected.delete(prob.id);
    cardEl.classList.remove('selected');
  } else {
    selected.set(prob.id, prob);
    cardEl.classList.add('selected');
  }
  updateSelUI();
}

function updateSelUI() {
  const n = selected.size;
  selNum.textContent = n;
  selCount.classList.toggle('hidden', n === 0);
  btnCompose.classList.toggle('hidden', n === 0);
}

btnSelAll.addEventListener('click', () => {
  allProblems.forEach(p => selected.set(p.id, p));
  renderGrid();
  updateSelUI();
});

btnSelNone.addEventListener('click', () => {
  allProblems.forEach(p => selected.delete(p.id));
  renderGrid();
  updateSelUI();
});

// ── 필터 이벤트 ───────────────────────────────────────────────────────
btnSearch.addEventListener('click', () => search(0));
btnClear.addEventListener('click', () => {
  fYear.value = ''; fExam.value = ''; fUnit.value = ''; fDiff.value = '';
  search(0);
});
[fYear, fExam, fUnit, fDiff].forEach(el =>
  el.addEventListener('keydown', e => { if (e.key === 'Enter') search(0); })
);

// ── 시험지 구성 모달 ──────────────────────────────────────────────────
btnCompose.addEventListener('click', openModal);
modalClose.addEventListener('click', closeModal);
modalBackdrop.addEventListener('click', closeModal);

function openModal() {
  renderComposeList();
  composeModal.classList.remove('hidden');
}
function closeModal() {
  composeModal.classList.add('hidden');
}

function renderComposeList() {
  const probs = [...selected.values()];
  modalCount.textContent = probs.length;
  composeList.innerHTML  = '';

  probs.forEach((p, i) => {
    const row = document.createElement('div');
    row.className = 'flex items-center gap-3 border border-border rounded-lg p-2 bg-white';
    row.innerHTML = `
      <span class="text-xs font-semibold text-gray-400 w-5 text-center">${i + 1}</span>
      <img src="${p.image_path}" class="w-16 h-12 object-contain bg-gray-50 rounded border border-border shrink-0" />
      <div class="flex-1 text-xs text-gray-600 min-w-0">
        <div class="font-medium truncate">${p.year} ${p.exam_type} ${p.number}번</div>
        <div class="text-gray-400">${p.unit || ''} ${p.difficulty ? '· ' + p.difficulty : ''}</div>
      </div>
      <button class="btn-remove text-gray-300 hover:text-red-500 text-sm" data-id="${p.id}">✕</button>
    `;
    row.querySelector('.btn-remove').addEventListener('click', () => {
      selected.delete(p.id);
      updateSelUI();
      renderGrid();
      renderComposeList();
      if (selected.size === 0) closeModal();
    });
    composeList.appendChild(row);
  });
}

// ── PDF 생성 ─────────────────────────────────────────────────────────
btnGenPdf.addEventListener('click', async () => {
  const probs = [...selected.values()];
  if (probs.length === 0) return;

  // DB 기출문제는 image_path 기반이므로 PDF에서 이미지 임베드 형태로 전달
  const problems = probs.map(p => ({
    type:       '선택형',
    score:      p.score || 3,
    text:       p.text || `${p.year}학년도 ${p.exam_type} ${p.number}번`,
    latex:      p.latex || '',
    choices:    p.choices || [],
    answer:     p.answer || '',
    image_path: p.image_path,   // 렌더러가 이미지 임베드에 사용
  }));

  const payload = {
    title:    document.getElementById('exam-title').value || '수학 기출문제',
    subtitle: document.getElementById('exam-subtitle').value || '',
    problems,
  };

  btnGenPdf.disabled = true;
  pdfSpinner.classList.remove('hidden');
  try {
    const form = new FormData();
    form.append('exam_json',    JSON.stringify(payload));
    form.append('with_answers', chkAnswers.checked ? 'true' : 'false');

    const res = await fetch('/pdf', { method: 'POST', body: form });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }

    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = (payload.title).replace(/\s+/g, '_') + '.pdf';
    a.click();
    URL.revokeObjectURL(url);
    closeModal();
  } catch (e) {
    alert('PDF 오류: ' + e.message);
  } finally {
    btnGenPdf.disabled = false;
    pdfSpinner.classList.add('hidden');
  }
});

// ── 초기 로드 ────────────────────────────────────────────────────────
search(0);
