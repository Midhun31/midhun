/**
 * script.js — TradeScope Frontend Application
 *
 * Responsibilities:
 *  - Auth guard (JWT check)
 *  - Sector chip rendering
 *  - API calls to /analyze/{sector}
 *  - Animated loading steps
 *  - Markdown → HTML rendering (no external lib)
 *  - Stats tracking
 */

'use strict';

// ── Config ─────────────────────────────────────────────────────────────────────
const API_BASE   = '';  // same origin
const SECTORS    = [
  'technology','agriculture','pharma','textile','automobile','energy',
  'finance','real_estate','fmcg','manufacturing','healthcare','education',
  'defence','infrastructure','chemicals',
];

// ── State ──────────────────────────────────────────────────────────────────────
let requestCount = 0;
let rawMarkdown  = '';

// ── DOM helpers ────────────────────────────────────────────────────────────────
const $  = (id) => document.getElementById(id);
const qs = (sel) => document.querySelector(sel);

// ── Auth Guard ─────────────────────────────────────────────────────────────────
function getToken() {
  const token  = sessionStorage.getItem('token');
  const expiry = +sessionStorage.getItem('tokenExpiry');
  if (!token || Date.now() > expiry) {
    sessionStorage.clear();
    window.location.href = 'login.html';
    return null;
  }
  return token;
}

function init() {
  const token    = getToken();
  if (!token) return;

  const username = sessionStorage.getItem('username') || 'user';
  $('header-username').textContent = username;

  renderSectorChips();
  attachEvents();
  setTimeout(initSearch, 0);
}
function initSearch() {
  const input = $('sector-search');
  const results = $('search-results');

  // ✅ Prevent crash if element missing
  if (!input || !results) {
    console.warn("Search elements not found");
    return;
  }

  input.addEventListener('input', () => {
    const query = input.value.toLowerCase().trim();

    if (!query) {
      results.innerHTML = '';
      return;
    }

    const filtered = SECTORS.filter(s =>
      s.toLowerCase().includes(query)
    );

    results.innerHTML = '';

    // Show matched sectors
    filtered.forEach(s => {
      const div = document.createElement('div');
      div.className = 'sector-chip';
      div.textContent = s.replace(/_/g, ' ');
      div.addEventListener('click', () => selectSector(s));
      results.appendChild(div);
    });

    // ✅ Always allow custom sector
    if (filtered.length === 0 || !filtered.includes(query)) {
      const div = document.createElement('div');
      div.className = 'sector-chip active';
      div.textContent = `➕ Use "${query}"`;
      div.addEventListener('click', () => selectSector(query));
      results.appendChild(div);
    }
  });
}
function selectSector(sector) {
  const input = $('sector-search');

  input.value = sector;
  input.dataset.selected = sector;

  $('analyze-btn').disabled = false;

  // clear suggestions
  $('search-results').innerHTML = '';
}
// ── Sector Chips ───────────────────────────────────────────────────────────────
function renderSectorChips() {
  const grid = $('sector-chips');
  grid.innerHTML = '';
  SECTORS.forEach(s => {
    const chip = document.createElement('button');
    chip.className   = 'sector-chip';
    chip.textContent = s.replace(/_/g, ' ');
    chip.dataset.sector = s;
    chip.addEventListener('click', () => {
      document.querySelectorAll('.sector-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      $('sector-search').value = s;
$('sector-search').dataset.selected = s;
      $('analyze-btn').disabled = false;
    });
    grid.appendChild(chip);
  });
}

// ── Events ─────────────────────────────────────────────────────────────────────
function attachEvents() {
  

  $('analyze-btn').addEventListener('click', runAnalysis);

  $('logout-btn').addEventListener('click', () => {
    sessionStorage.clear();
    window.location.href = 'login.html';
  });

  $('copy-btn').addEventListener('click', () => {
    navigator.clipboard.writeText(rawMarkdown).then(() => {
      $('copy-btn').textContent = 'Copied!';
      setTimeout(() => ($('copy-btn').textContent = 'Copy Markdown'), 2000);
    });
  });

  $('new-btn').addEventListener('click', resetUI);
}

// ── Analysis Flow ──────────────────────────────────────────────────────────────
async function runAnalysis() {
  const sector = $('sector-search').dataset.selected || $('sector-search').value;
  if (!sector) return;

  const token = getToken();
  if (!token) return;

  hideError();
  showLoading();
  const startTime = Date.now();

  // Animate loading steps
  const stepIds = ['step-1','step-2','step-3','step-4'];
  const delays  = [0, 600, 1400, 2500];
  stepIds.forEach((id, i) => {
    setTimeout(() => activateStep(id), delays[i]);
  });

  try {
    const res = await fetch(`${API_BASE}/analyze/${encodeURIComponent(sector)}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept':        'application/json',
      },
    });

    const data = await res.json();

    if (!res.ok) {
      if (res.status === 429) {
        const rl = data.rate_limit;
        showError(
          `Rate limit reached. You've made ${rl?.requests_made || '?'}/${rl?.requests_limit || 10} requests. ` +
          `Reset in ${rl?.reset_in_seconds || 60}s.`
        );
      } else if (res.status === 401) {
        sessionStorage.clear();
        window.location.href = 'login.html';
      } else {
        showError(data.detail || `Error ${res.status}: Analysis failed.`);
      }
      hideLoading();
      return;
    }

    // Mark all steps done
    stepIds.forEach(id => doneStep(id));

    await sleep(400); // brief pause for UX

    // Update stats
    requestCount++;
    $('stat-requests').textContent  = requestCount;
    $('stat-last-sector').textContent = sector.replace(/_/g,' ');
    $('stat-time').textContent      = ((Date.now() - startTime) / 1000).toFixed(1) + 's';

    // Render report
    renderReport(data);

  } catch (err) {
    showError('Network error — is the backend server running on port 8000?');
    console.error(err);
    hideLoading();
  }
}

// ── Markdown Renderer ──────────────────────────────────────────────────────────
/**
 * Lightweight markdown → HTML converter.
 * Handles: h1, h2, h3, ul/li, **bold**, *italic*, `code`, paragraphs.
 */
function renderMarkdown(md) {
  const lines  = md.split('\n');
  const html   = [];
  let inUl     = false;

  function closeUl() {
    if (inUl) { html.push('</ul>'); inUl = false; }
  }

  function escapeSafe(s) {
    return s
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;');
  }

  function inlineFormat(s) {
    return escapeSafe(s)
      .replace(/\*\*(.+?)\*\*/g,  '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g,      '<em>$1</em>')
      .replace(/`(.+?)`/g,        '<code>$1</code>');
  }

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (line.startsWith('# ')) {
      closeUl();
      html.push(`<h1>${inlineFormat(line.slice(2))}</h1>`);
    } else if (line.startsWith('## ')) {
      closeUl();
      html.push(`<h2>${inlineFormat(line.slice(3))}</h2>`);
    } else if (line.startsWith('### ')) {
      closeUl();
      html.push(`<h3>${inlineFormat(line.slice(4))}</h3>`);
    } else if (/^[-*] /.test(line)) {
      if (!inUl) { html.push('<ul>'); inUl = true; }
      html.push(`<li>${inlineFormat(line.slice(2))}</li>`);
    } else if (line === '') {
      closeUl();
      // blank line — paragraph separator handled below
    } else {
      closeUl();
      html.push(`<p>${inlineFormat(line)}</p>`);
    }
  }

  closeUl();
  return html.join('\n');
}

function renderReport(data) {
  rawMarkdown = data.report;

  // Set metadata
  $('report-sector-tag').textContent = data.sector.replace(/_/g,' ').toUpperCase();
  $('report-timestamp').textContent  = formatDate(data.generated_at);

  // Render markdown
  $('markdown-content').innerHTML = renderMarkdown(data.report);

  // Render sources
  if (data.data_sources && data.data_sources.length > 0) {
    const list = $('sources-list');
    list.innerHTML = '';
    data.data_sources.forEach(src => {
      const chip = document.createElement('span');
      chip.className   = 'source-chip';
      chip.textContent = src;
      chip.title       = src;
      list.appendChild(chip);
    });
    $('sources-card').style.display = 'block';
  }

  hideLoading();
  $('report-output').style.display = 'block';
}

// ── UI State Helpers ───────────────────────────────────────────────────────────
function showLoading() {
  $('report-output').style.display  = 'none';
  $('error-alert').style.display    = 'none';
  $('loading-state').style.display  = 'block';
  $('btn-text').style.display       = 'none';
  $('btn-spinner').style.display    = 'inline-block';
  $('analyze-btn').disabled         = true;

  // Reset step states
  ['step-1','step-2','step-3','step-4'].forEach(id => {
    const el = $(id);
    el.classList.remove('active','done');
  });
}

function hideLoading() {
  $('loading-state').style.display  = 'none';
  $('btn-text').style.display       = 'inline';
  $('btn-spinner').style.display    = 'none';
  $('analyze-btn').disabled         = false;
}

function activateStep(id) {
  // Mark previous step done
  const ids = ['step-1','step-2','step-3','step-4'];
  const idx = ids.indexOf(id);
  if (idx > 0) doneStep(ids[idx-1]);
  $(id)?.classList.add('active');
}

function doneStep(id) {
  const el = $(id);
  if (!el) return;
  el.classList.remove('active');
  el.classList.add('done');
}

function showError(msg) {
  const el = $('error-alert');
  el.textContent  = msg;
  el.style.display = 'block';
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
  $('error-alert').style.display = 'none';
}

function resetUI() {
  $('report-output').style.display  = 'none';
  $('sources-card').style.display   = 'none';
  $('sector-search').value = '';
delete $('sector-search').dataset.selected;
  $('analyze-btn').disabled         = true;
  document.querySelectorAll('.sector-chip').forEach(c => c.classList.remove('active'));
  rawMarkdown = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Utils ──────────────────────────────────────────────────────────────────────
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function formatDate(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleString('en-IN', {
      day:'numeric', month:'short', year:'numeric',
      hour:'2-digit', minute:'2-digit', hour12:true,
    });
  } catch { return isoStr; }
}

// ── Boot ───────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
