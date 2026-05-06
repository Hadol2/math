'use strict';

// 헤더 오른쪽에 로그인 상태 표시
(async function initAuthHeader() {
  const area = document.getElementById('auth-area');
  if (!area) return;

  try {
    const res = await fetch('/auth/me');
    if (res.ok) {
      const user = await res.json();
      const planBadge = user.plan === 'pro'
        ? '<span class="px-1.5 py-0.5 rounded text-xs bg-amber-100 text-amber-700 font-medium">Pro</span>'
        : (user.daily_limit != null
            ? `<span class="text-xs text-gray-400">${user.variants_today}/${user.daily_limit}</span>`
            : '');

      area.innerHTML = `
        <span class="text-gray-600">${user.name}</span>
        ${planBadge}
        <button onclick="logout()"
                class="text-xs text-gray-400 hover:text-gray-700 transition-colors">로그아웃</button>
      `;
    } else {
      area.innerHTML = `
        <a href="/static/login.html?next=${encodeURIComponent(location.pathname + location.search)}"
           class="px-3 py-1.5 rounded-lg border border-border text-xs text-gray-600 hover:bg-gray-50 transition-colors">
          로그인
        </a>
      `;
    }
  } catch (_) {
    // 네트워크 오류 시 조용히 무시
  }
})();

async function logout() {
  await fetch('/auth/logout', { method: 'POST' });
  location.href = '/static/login.html';
}
