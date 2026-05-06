'use strict';

// ── 상태 ─────────────────────────────────────────────────────────────
let problems = [];   // [{type, score, text, latex, choices, answer}, ...]
let nextId = 0;      // 카드 DOM id 생성용

// ── DOM 참조 ──────────────────────────────────────────────────────────
const dropZone        = document.getElementById('drop-zone');
const fileInput       = document.getElementById('file-input');
const btnExtract      = document.getElementById('btn-extract');
const previewContainer = document.getElementById('preview-container');
const spinner         = document.getElementById('spinner');
const spinnerText     = document.getElementById('spinner-text');
const problemsSection = document.getElementById('problems-section');
const problemList     = document.getElementById('problem-list');
const btnAddProblem   = document.getElementById('btn-add-problem');
const btnVariantsAll  = document.getElementById('btn-variants-all');
const btnPdfPreview   = document.getElementById('btn-pdf-preview');
const chkAnswers      = document.getElementById('chk-answers');
const btnDownload     = document.getElementById('btn-download-pdf');
const examTitle       = document.getElementById('exam-title');
const examSubtitle    = document.getElementById('exam-subtitle');
const cardTpl         = document.getElementById('problem-card-tpl');

// ── 파일 업로드 ───────────────────────────────────────────────────────
let selectedFile = null;

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
  previewContainer.innerHTML = '';
  previewContainer.classList.remove('hidden');
  const img = document.createElement('img');
  img.src = URL.createObjectURL(file);
  img.className = 'h-32 rounded-lg border border-border object-contain';
  previewContainer.appendChild(img);
  btnExtract.classList.remove('hidden');
}

// ── 문제 추출 ─────────────────────────────────────────────────────────
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
    problems = data.problems;
    renderAllProblems();
    problemsSection.classList.remove('hidden');
  } catch (e) {
    alert('추출 오류: ' + e.message);
  } finally {
    hideSpinner();
    btnExtract.disabled = false;
  }
});

// ── 문제 카드 렌더링 ──────────────────────────────────────────────────
function renderAllProblems() {
  problemList.innerHTML = '';
  problems.forEach((p, i) => renderCard(p, i));
}

function renderCard(prob, idx) {
  const node = cardTpl.content.cloneNode(true);
  const card = node.querySelector('.problem-card');
  const id = `prob-${nextId++}`;
  card.dataset.idx = idx;

  card.querySelector('.prob-num').textContent = `${idx + 1}.`;

  const typeEl    = card.querySelector('.field-type');
  const scoreEl   = card.querySelector('.field-score');
  const textEl    = card.querySelector('.field-text');
  const latexEl   = card.querySelector('.field-latex');
  const answerEl  = card.querySelector('.field-answer');
  const choicesEl = card.querySelector('.choices-list');
  const choicesBlock = card.querySelector('.choices-block');

  typeEl.value   = prob.type  || '선택형';
  scoreEl.value  = prob.score || 3;
  textEl.value   = prob.text  || '';
  latexEl.value  = prob.latex || '';
  answerEl.value = prob.answer || '';

  const CIRCLES = ['①', '②', '③', '④', '⑤'];
  (prob.choices || ['','','','','']).forEach((ch, ci) => {
    const inp = document.createElement('input');
    inp.type = 'text';
    inp.value = ch;
    inp.placeholder = `${CIRCLES[ci]} 보기`;
    inp.className = 'w-full border border-border rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-accent/40';
    inp.addEventListener('input', () => { problems[card.dataset.idx].choices[ci] = inp.value; });
    choicesEl.appendChild(inp);
  });

  // 서술형이면 보기 숨김
  function updateVisibility() {
    choicesBlock.style.display = typeEl.value === '서술형' ? 'none' : '';
  }
  updateVisibility();
  typeEl.addEventListener('change', updateVisibility);

  // 필드 → state 동기화
  typeEl.addEventListener('change',  () => { problems[card.dataset.idx].type   = typeEl.value; });
  scoreEl.addEventListener('input',  () => { problems[card.dataset.idx].score  = parseInt(scoreEl.value) || 3; });
  textEl.addEventListener('input',   () => { problems[card.dataset.idx].text   = textEl.value; });
  latexEl.addEventListener('input',  () => { problems[card.dataset.idx].latex  = latexEl.value; });
  answerEl.addEventListener('input', () => { problems[card.dataset.idx].answer = answerEl.value; });

  // 변형 버튼
  card.querySelector('.btn-variant').addEventListener('click', () => variantOne(parseInt(card.dataset.idx)));

  // 삭제 버튼
  card.querySelector('.btn-delete').addEventListener('click', () => {
    const i = parseInt(card.dataset.idx);
    problems.splice(i, 1);
    renderAllProblems();
  });

  problemList.appendChild(node);
}

// ── 문제 추가 ─────────────────────────────────────────────────────────
btnAddProblem.addEventListener('click', () => {
  problems.push({ type: '선택형', score: 3, text: '', latex: '', choices: ['','','','',''], answer: '' });
  renderAllProblems();
  problemsSection.classList.remove('hidden');
});

// ── 단일 변형 ─────────────────────────────────────────────────────────
async function variantOne(idx) {
  showSpinner('변형 생성 중...');
  try {
    const form = new FormData();
    form.append('problem_json', JSON.stringify(problems[idx]));
    form.append('n', '3');
    const res = await fetch('/variants', { method: 'POST', body: form });
    if (res.status === 401) { location.href = '/static/login.html?next=' + encodeURIComponent(location.pathname); return; }
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    problems.splice(idx + 1, 0, ...data.variants);
    renderAllProblems();
  } catch (e) {
    alert('변형 오류: ' + e.message);
  } finally {
    hideSpinner();
  }
}

// ── 전체 변형 ─────────────────────────────────────────────────────────
btnVariantsAll.addEventListener('click', async () => {
  if (problems.length === 0) return;
  showSpinner('전체 변형 생성 중 (문제 수 × 약 15초)...');
  try {
    const originals = [...problems];
    const all = [];
    for (const p of originals) {
      all.push(p);
      const form = new FormData();
      form.append('problem_json', JSON.stringify(p));
      form.append('n', '3');
      const res = await fetch('/variants', { method: 'POST', body: form });
      if (res.status === 401) { location.href = '/static/login.html?next=' + encodeURIComponent(location.pathname); return; }
      if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
      const data = await res.json();
      all.push(...data.variants);
    }
    problems = all;
    renderAllProblems();
  } catch (e) {
    alert('전체 변형 오류: ' + e.message);
  } finally {
    hideSpinner();
  }
});

// ── PDF 생성 ─────────────────────────────────────────────────────────
btnPdfPreview.addEventListener('click', () => downloadPdf());
btnDownload.addEventListener('click', (e) => { e.preventDefault(); downloadPdf(); });

async function downloadPdf() {
  if (problems.length === 0) { alert('문제가 없습니다.'); return; }
  showSpinner('PDF 생성 중...');
  try {
    const payload = {
      title:    examTitle.value || '수학 시험지',
      subtitle: examSubtitle.value || '',
      problems,
    };
    const form = new FormData();
    form.append('exam_json', JSON.stringify(payload));
    form.append('with_answers', chkAnswers.checked ? 'true' : 'false');

    const res = await fetch('/pdf', { method: 'POST', body: form });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (examTitle.value || '수학시험지').replace(/\s+/g, '_') + '.pdf';
    a.click();
    URL.revokeObjectURL(url);

    btnDownload.classList.remove('hidden');
  } catch (e) {
    alert('PDF 오류: ' + e.message);
  } finally {
    hideSpinner();
  }
}

// ── 유틸 ─────────────────────────────────────────────────────────────
function showSpinner(msg) {
  spinnerText.textContent = msg;
  spinner.classList.remove('hidden');
}
function hideSpinner() {
  spinner.classList.add('hidden');
}
