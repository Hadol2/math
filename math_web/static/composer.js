'use strict';

// ── 상태 ─────────────────────────────────────────────────────────────
let examProblems = [];   // [{_src:'db'|'manual'|'extracted', ...}, ...]
let currentFmt   = 'suneung';

// ── DOM ──────────────────────────────────────────────────────────────
const tabDbBtn       = document.getElementById('tab-db-btn');
const tabImgBtn      = document.getElementById('tab-img-btn');
const tabDb          = document.getElementById('tab-db');
const tabImg         = document.getElementById('tab-img');
const composeList    = document.getElementById('compose-list');
const emptyComposer  = document.getElementById('empty-composer');
const probCount      = document.getElementById('prob-count');
const spinner        = document.getElementById('spinner');
const spinnerText    = document.getElementById('spinner-text');
const chkAnswers     = document.getElementById('chk-answers');
const btnPdf         = document.getElementById('btn-pdf');
const btnVariantsAll = document.getElementById('btn-variants-all');
const btnAddProblem  = document.getElementById('btn-add-problem');
const examTitle      = document.getElementById('exam-title');
const examSubtitle   = document.getElementById('exam-subtitle');
const shortfallBox   = document.getElementById('shortfall-box');
const shortfallList  = document.getElementById('shortfall-list');

// ── 탭 전환 ──────────────────────────────────────────────────────────
tabDbBtn.addEventListener('click', () => {
  tabDb.classList.remove('hidden');
  tabImg.classList.add('hidden');
  tabDbBtn.className  = 'flex-1 py-2.5 text-white bg-gray-900 transition-colors';
  tabImgBtn.className = 'flex-1 py-2.5 text-gray-500 hover:bg-gray-50 transition-colors';
});
tabImgBtn.addEventListener('click', () => {
  tabImg.classList.remove('hidden');
  tabDb.classList.add('hidden');
  tabImgBtn.className = 'flex-1 py-2.5 text-white bg-gray-900 transition-colors';
  tabDbBtn.className  = 'flex-1 py-2.5 text-gray-500 hover:bg-gray-50 transition-colors';
});

// ── 형식 선택 ────────────────────────────────────────────────────────
const fmtBtns = document.querySelectorAll('.fmt-btn');
fmtBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    currentFmt = btn.dataset.fmt;
    fmtBtns.forEach(b => {
      b.className = 'fmt-btn py-2 rounded-lg border text-xs font-medium transition-colors border-border text-gray-600 hover:bg-gray-50';
    });
    btn.className = 'fmt-btn py-2 rounded-lg border text-xs font-medium transition-colors border-gray-900 bg-gray-900 text-white';
    document.getElementById('fmt-suneung-config').classList.toggle('hidden', currentFmt !== 'suneung');
    document.getElementById('fmt-naeshin-config').classList.toggle('hidden', currentFmt !== 'naeshin');
    document.getElementById('fmt-custom-config').classList.toggle('hidden',  currentFmt !== 'custom');
    updateDefaultRatio();
  });
});

function updateDefaultRatio() {
  // 형식 바꿔도 난이도 프리셋은 유지 (사용자가 별도로 선택)
}

// ── 난이도 프리셋 ────────────────────────────────────────────────────
let diffH = 30, diffM = 50, diffL = 20;

const ratioDisplay     = document.getElementById('ratio-display');
const customRatioInputs = document.getElementById('custom-ratio-inputs');
const ratioHigh        = document.getElementById('ratio-high');
const ratioMid         = document.getElementById('ratio-mid');
const ratioLow         = document.getElementById('ratio-low');
const ratioTotal       = document.getElementById('ratio-total');

function applyPreset(h, m, l) {
  diffH = h; diffM = m; diffL = l;
  ratioHigh.value = h; ratioMid.value = m; ratioLow.value = l;
  ratioDisplay.innerHTML =
    `<span class="text-red-400">상 ${h}%</span> · <span class="text-amber-400">중 ${m}%</span> · <span class="text-green-500">하 ${l}%</span>`;
}

document.querySelectorAll('.diff-preset').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.diff-preset').forEach(b => {
      b.className = 'diff-preset py-2 rounded-lg border text-xs font-medium transition-colors border-border text-gray-600 hover:bg-gray-50';
    });
    btn.className = 'diff-preset py-2 rounded-lg border text-xs font-medium transition-colors border-gray-900 bg-gray-900 text-white';

    if (btn.id === 'diff-custom-btn') {
      customRatioInputs.classList.remove('hidden');
      ratioDisplay.classList.add('hidden');
    } else {
      customRatioInputs.classList.add('hidden');
      ratioDisplay.classList.remove('hidden');
      applyPreset(parseInt(btn.dataset.h), parseInt(btn.dataset.m), parseInt(btn.dataset.l));
    }
  });
});

function updateCustomRatio() {
  diffH = parseInt(ratioHigh.value) || 0;
  diffM = parseInt(ratioMid.value)  || 0;
  diffL = parseInt(ratioLow.value)  || 0;
  const total = diffH + diffM + diffL;
  const b = ratioTotal.querySelector('b');
  b.textContent = total;
  b.className   = total === 100 ? 'text-gray-700' : 'text-red-500';
}
[ratioHigh, ratioMid, ratioLow].forEach(el => el.addEventListener('input', updateCustomRatio));

// ── 단원 전체 선택 ───────────────────────────────────────────────────
document.getElementById('btn-unit-all').addEventListener('click', () => {
  document.querySelectorAll('.unit-chk').forEach(chk => { chk.checked = true; });
});

// ── 연도 드롭다운 채우기 ─────────────────────────────────────────────
(function populateYears() {
  const cur = new Date().getFullYear();
  const fromSel = document.getElementById('year-from');
  const toSel   = document.getElementById('year-to');
  for (let y = cur; y >= 1994; y--) {
    const a = new Option(y + '학년도', y);
    const b = new Option(y + '학년도', y);
    if (y === 2020) a.selected = true;
    if (y === cur)  b.selected = true;
    fromSel.appendChild(a);
    toSel.appendChild(b);
  }
})();

// ── 자동 구성 (문제은행) ─────────────────────────────────────────────
function calcNTotal() {
  if (currentFmt === 'suneung') return 30;
  if (currentFmt === 'naeshin') {
    return (parseInt(document.getElementById('n-choice').value) || 0) +
           (parseInt(document.getElementById('n-essay').value)  || 0);
  }
  return parseInt(document.getElementById('n-custom').value) || 30;
}

document.getElementById('btn-auto-compose').addEventListener('click', async () => {
  const h = diffH, m = diffM, l = diffL;
  if (h + m + l !== 100) { alert('난이도 비율 합계가 100%여야 합니다.\n(커스텀 모드에서 상·중·하 합계를 100%로 맞춰주세요)'); return; }

  const units = [...document.querySelectorAll('.unit-chk:checked')].map(c => c.value);
  const nTotal = calcNTotal();
  if (nTotal <= 0) { alert('문항 수를 입력해 주세요.'); return; }

  const body = {
    units,
    year_from:        parseInt(document.getElementById('year-from').value) || null,
    year_to:          parseInt(document.getElementById('year-to').value)   || null,
    difficulty_ratio: { 상: h, 중: m, 하: l },
    n_total:          nTotal,
  };

  showSpinner('문제 구성 중...');
  shortfallBox.classList.add('hidden');
  try {
    const res  = await fetch('/db/compose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();

    // DB 문제를 examProblems에 추가 (중복 제거)
    const existingIds = new Set(examProblems.filter(p => p._src === 'db').map(p => p.id));
    const newProbs = data.problems.filter(p => !existingIds.has(p.id))
      .map(p => ({ ...p, _src: 'db' }));
    examProblems.push(...newProbs);
    renderComposer();

    // 부족 경고
    if (data.shortfalls && Object.keys(data.shortfalls).length > 0) {
      shortfallList.innerHTML = '';
      Object.entries(data.shortfalls).forEach(([d, info]) => {
        const li = document.createElement('p');
        li.textContent = `${d} 난이도: ${info.needed}문제 필요, ${info.available}개만 있음 (${info.needed - info.available}문제 부족)`;
        shortfallList.appendChild(li);
      });
      shortfallBox.classList.remove('hidden');
    }
  } catch (e) {
    alert('구성 오류: ' + e.message);
  } finally {
    hideSpinner();
  }
});

// ── 이미지 업로드 & 추출 ─────────────────────────────────────────────
let selectedFile = null;
const dropZone   = document.getElementById('drop-zone');
const fileInput  = document.getElementById('file-input');
const uploadPreview = document.getElementById('upload-preview');
const previewImg    = document.getElementById('preview-img');
const btnExtract    = document.getElementById('btn-extract');

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('border-accent'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('border-accent'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('border-accent');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

function setFile(file) {
  selectedFile = file;
  previewImg.src = URL.createObjectURL(file);
  uploadPreview.classList.remove('hidden');
  btnExtract.classList.remove('hidden');
}

btnExtract.addEventListener('click', async () => {
  if (!selectedFile) return;
  showSpinner('이미지 분석 중 (첫 실행은 20~30초)...');
  btnExtract.disabled = true;
  try {
    const form = new FormData();
    form.append('file', selectedFile);
    const res = await fetch('/extract', { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    const extracted = data.problems.map(p => ({ ...p, _src: 'extracted' }));
    examProblems.push(...extracted);
    renderComposer();
  } catch (e) {
    alert('추출 오류: ' + e.message);
  } finally {
    hideSpinner();
    btnExtract.disabled = false;
  }
});

// ── 직접 입력 문제 추가 ──────────────────────────────────────────────
btnAddProblem.addEventListener('click', () => {
  examProblems.push({
    _src:    'manual',
    type:    '선택형',
    score:   3,
    text:    '',
    latex:   '',
    choices: ['', '', '', '', ''],
    answer:  '',
  });
  renderComposer();
});

// ── 렌더링 ───────────────────────────────────────────────────────────
function renderComposer() {
  probCount.textContent = examProblems.length;
  emptyComposer.classList.toggle('hidden', examProblems.length > 0);
  composeList.innerHTML = '';

  examProblems.forEach((p, idx) => {
    if (p._src === 'db') {
      composeList.appendChild(makeDbCard(p, idx));
    } else {
      composeList.appendChild(makeManualCard(p, idx));
    }
  });
}

function makeDbCard(p, idx) {
  const diffColor = { 상: 'text-red-500', 중: 'text-amber-500', 하: 'text-green-600' }[p.difficulty] || 'text-gray-400';
  const div = document.createElement('div');
  div.className = 'bg-white border border-border rounded-xl flex items-center gap-3 p-3';
  div.innerHTML = `
    <span class="text-xs font-semibold text-gray-400 w-5 text-center shrink-0">${idx + 1}</span>
    <img src="${p.image_path}" class="w-20 h-14 object-contain bg-gray-50 rounded border border-border shrink-0" loading="lazy" />
    <div class="flex-1 min-w-0 text-xs text-gray-600">
      <div class="font-semibold text-gray-800 truncate">${p.year} ${p.exam_type} ${p.number}번</div>
      <div class="text-gray-400 mt-0.5 flex gap-1.5 flex-wrap">
        <span>${p.unit || '단원미정'}</span>
        ${p.difficulty ? `<span class="font-medium ${diffColor}">· ${p.difficulty}</span>` : ''}
        <span class="text-gray-300">· ${p.score || 3}점</span>
      </div>
      ${p.answer ? `<div class="text-gray-400 mt-0.5">정답: <span class="font-medium text-gray-600">${p.answer}</span></div>` : ''}
    </div>
    <div class="flex flex-col gap-1 shrink-0 text-xs">
      <button class="btn-up text-gray-400 hover:text-gray-700">↑</button>
      <button class="btn-dn text-gray-400 hover:text-gray-700">↓</button>
      <button class="btn-variant text-accent hover:underline">변형</button>
      <button class="btn-remove text-gray-300 hover:text-red-500">✕</button>
    </div>
  `;
  div.querySelector('.btn-up').addEventListener('click', () => moveItem(idx, -1));
  div.querySelector('.btn-dn').addEventListener('click', () => moveItem(idx, +1));
  div.querySelector('.btn-variant').addEventListener('click', () => variantOne(idx));
  div.querySelector('.btn-remove').addEventListener('click', () => { examProblems.splice(idx, 1); renderComposer(); });
  return div;
}

function makeManualCard(p, idx) {
  const tpl  = document.getElementById('manual-card-tpl');
  const node = tpl.content.cloneNode(true);
  const card = node.querySelector('.manual-card');

  // prepend index number
  const numSpan = document.createElement('span');
  numSpan.className = 'text-xs font-semibold text-gray-400 mb-1 block';
  numSpan.textContent = `${idx + 1}.`;
  card.insertBefore(numSpan, card.firstChild);

  const typeEl    = card.querySelector('.field-type');
  const scoreEl   = card.querySelector('.field-score');
  const textEl    = card.querySelector('.field-text');
  const latexEl   = card.querySelector('.field-latex');
  const answerEl  = card.querySelector('.field-answer');
  const choicesList = card.querySelector('.choices-list');
  const choicesBlock = card.querySelector('.choices-block');

  typeEl.value   = p.type   || '선택형';
  scoreEl.value  = p.score  || 3;
  textEl.value   = p.text   || '';
  latexEl.value  = p.latex  || '';
  answerEl.value = p.answer || '';

  const CIRCLES = ['①', '②', '③', '④', '⑤'];
  (p.choices || ['','','','','']).forEach((ch, ci) => {
    const inp = document.createElement('input');
    inp.type = 'text'; inp.value = ch;
    inp.placeholder = `${CIRCLES[ci]} 보기`;
    inp.className = 'w-full border border-border rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-accent/40';
    inp.addEventListener('input', () => { examProblems[idx].choices[ci] = inp.value; });
    choicesList.appendChild(inp);
  });

  function syncVisibility() {
    choicesBlock.style.display = typeEl.value === '서술형' ? 'none' : '';
  }
  syncVisibility();
  typeEl.addEventListener('change',  () => { examProblems[idx].type   = typeEl.value; syncVisibility(); });
  scoreEl.addEventListener('input',  () => { examProblems[idx].score  = parseInt(scoreEl.value) || 3; });
  textEl.addEventListener('input',   () => { examProblems[idx].text   = textEl.value; });
  latexEl.addEventListener('input',  () => { examProblems[idx].latex  = latexEl.value; });
  answerEl.addEventListener('input', () => { examProblems[idx].answer = answerEl.value; });

  card.querySelector('.btn-variant').addEventListener('click', () => variantOne(idx));
  card.querySelector('.btn-remove').addEventListener('click', () => { examProblems.splice(idx, 1); renderComposer(); });
  return card;
}

// ── 순서 이동 ────────────────────────────────────────────────────────
function moveItem(idx, dir) {
  const target = idx + dir;
  if (target < 0 || target >= examProblems.length) return;
  [examProblems[idx], examProblems[target]] = [examProblems[target], examProblems[idx]];
  renderComposer();
}

// ── 개별 변형 ────────────────────────────────────────────────────────
async function variantOne(idx) {
  const p = examProblems[idx];
  if (p._src === 'db' && !p.text && !p.latex) {
    alert('이 문제는 텍스트/LaTeX 정보가 없어 변형을 생성하기 어렵습니다.\n기출 입력 페이지에서 텍스트를 추가해 주세요.');
    return;
  }
  showSpinner('변형 생성 중...');
  try {
    const form = new FormData();
    form.append('problem_json', JSON.stringify(p));
    form.append('n', '3');
    const res = await fetch('/variants', { method: 'POST', body: form });
    if (res.status === 401) { location.href = '/static/login.html?next=' + encodeURIComponent(location.pathname); return; }
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    const variants = data.variants.map(v => ({ ...v, _src: 'extracted' }));
    examProblems.splice(idx + 1, 0, ...variants);
    renderComposer();
  } catch (e) {
    alert('변형 오류: ' + e.message);
  } finally {
    hideSpinner();
  }
}

// ── 전체 변형 ────────────────────────────────────────────────────────
btnVariantsAll.addEventListener('click', async () => {
  if (examProblems.length === 0) return;
  showSpinner('전체 변형 생성 중 (문제 수 × 약 15초)...');
  try {
    const originals = [...examProblems];
    const all = [];
    for (const p of originals) {
      all.push(p);
      if (p._src === 'db' && !p.text && !p.latex) continue;
      const form = new FormData();
      form.append('problem_json', JSON.stringify(p));
      form.append('n', '3');
      const res = await fetch('/variants', { method: 'POST', body: form });
      if (res.status === 401) { location.href = '/static/login.html?next=' + encodeURIComponent(location.pathname); return; }
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const data = await res.json();
      all.push(...data.variants.map(v => ({ ...v, _src: 'extracted' })));
    }
    examProblems = all;
    renderComposer();
  } catch (e) {
    alert('전체 변형 오류: ' + e.message);
  } finally {
    hideSpinner();
  }
});

// ── PDF 생성 ─────────────────────────────────────────────────────────
btnPdf.addEventListener('click', async () => {
  if (examProblems.length === 0) { alert('문제가 없습니다.'); return; }
  showSpinner('PDF 생성 중...');
  try {
    const problems = examProblems.map(p => ({
      type:       p.type       || '선택형',
      score:      p.score      || 3,
      text:       p.text       || (p._src === 'db' ? `${p.year}학년도 ${p.exam_type} ${p.number}번` : ''),
      latex:      p.latex      || '',
      choices:    p.choices    || [],
      answer:     p.answer     || '',
      image_path: p.image_path || '',
    }));
    const payload = {
      title:    examTitle.value || '수학 시험지',
      subtitle: examSubtitle.value || '',
      problems,
    };
    const form = new FormData();
    form.append('exam_json',    JSON.stringify(payload));
    form.append('with_answers', chkAnswers.checked ? 'true' : 'false');

    const res = await fetch('/pdf', { method: 'POST', body: form });
    if (!res.ok) { const e = await res.json(); throw new Error(e.detail || res.statusText); }
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = (examTitle.value || '수학시험지').replace(/\s+/g, '_') + '.pdf';
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('PDF 오류: ' + e.message);
  } finally {
    hideSpinner();
  }
});

// ── 유틸 ─────────────────────────────────────────────────────────────
function showSpinner(msg) {
  spinnerText.textContent = msg;
  spinner.classList.remove('hidden');
}
function hideSpinner() {
  spinner.classList.add('hidden');
}

// 초기 비율 표시 (표준 기본값)
applyPreset(30, 50, 20);
