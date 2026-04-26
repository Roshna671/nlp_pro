/* ═══════════════════════════════════════════════════════════════
   BiasLens — Product-Grade Frontend Logic
   ═══════════════════════════════════════════════════════════════ */

const API = '';
let currentAnalysis = null;
let articleCount = 0;

document.addEventListener('DOMContentLoaded', () => {
  addArticleEntry();
  addArticleEntry();
  loadHistory();
  loadStats();
});

/* ── Tabs ─────────────────────────────────────────────────────── */
function switchTab(id) {
  document.querySelectorAll('.header-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelector(`.header-tab[data-tab="${id}"]`).classList.add('active');
  document.getElementById(`panel-${id}`).classList.add('active');
}

/* ── Article Entries ──────────────────────────────────────────── */
function addArticleEntry() {
  articleCount++;
  const c = document.getElementById('articleEntries');
  const el = document.createElement('div');
  el.className = 'article-card';
  el.id = `entry-${articleCount}`;
  el.innerHTML = `
    <div class="article-card-head">
      <span class="article-card-num">SOURCE #${articleCount}</span>
      <button class="btn-x" onclick="removeEntry('entry-${articleCount}')">&times;</button>
    </div>
    <div class="article-card-fields">
      <input type="text" class="source-name" placeholder="Source name (e.g., BBC News)">
      <textarea class="article-text" placeholder="Paste article text here…" rows="3"></textarea>
    </div>`;
  c.appendChild(el);
}

function removeEntry(id) {
  if (document.querySelectorAll('.article-card').length <= 1) return;
  document.getElementById(id).remove();
}

function fillSource(el) {
  const name = el.dataset.source;
  const entries = document.querySelectorAll('.article-card');
  for (const e of entries) {
    const inp = e.querySelector('.source-name');
    if (!inp.value.trim()) { inp.value = name; return; }
  }
  addArticleEntry();
  const all = document.querySelectorAll('.article-card');
  all[all.length - 1].querySelector('.source-name').value = name;
}

/* ── Analysis ─────────────────────────────────────────────────── */
async function runAnalysis() {
  const topic = document.getElementById('topicInput').value.trim();
  if (!topic) { shake(document.getElementById('topicInput')); return; }

  const entries = document.querySelectorAll('.article-card');
  const articles = [];
  let ok = true;

  entries.forEach(e => {
    const s = e.querySelector('.source-name').value.trim();
    const t = e.querySelector('.article-text').value.trim();
    if (!s || !t) { ok = false; shake(e); return; }
    articles.push({ source_name: s, text: t });
  });

  if (!ok || !articles.length) return;

  setLoading(true);
  try {
    const r = await fetch(`${API}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, articles })
    });
    if (!r.ok) throw new Error(await r.text());
    currentAnalysis = await r.json();
    render(currentAnalysis);
    loadHistory();
    loadStats();
    switchTab('scores');
  } catch (err) {
    alert('Analysis failed: ' + err.message);
  } finally {
    setLoading(false);
  }
}

/* ── Render ────────────────────────────────────────────────────── */
function render(d) {
  renderMetrics(d);
  renderTable(d);
  renderKeywords(d);
  renderRadar(d);
  document.getElementById('scoreDesc').textContent =
    `Topic: "${d.topic}" — ${d.total_sources} sources analyzed.`;
}

function renderMetrics(d) {
  const neutral = d.articles.filter(a => a.bias_label === 'Neutral').length;
  const warn = d.articles.filter(a => a.bias_label !== 'Neutral').length;

  document.getElementById('metricsGrid').innerHTML = `
    <div class="metric">
      <div class="metric-head">
        <div class="metric-icon green">✅</div>
        <span class="metric-trend flat">${neutral}/${d.total_sources}</span>
      </div>
      <div class="metric-value">${neutral}</div>
      <div class="metric-label">Neutral Sources</div>
    </div>
    <div class="metric">
      <div class="metric-head">
        <div class="metric-icon amber">⚠️</div>
        <span class="metric-trend ${warn > 0 ? 'down' : 'flat'}">${warn > 0 ? '!' + warn : '—'}</span>
      </div>
      <div class="metric-value">${warn}</div>
      <div class="metric-label">Biased / Leaning</div>
    </div>
    <div class="metric">
      <div class="metric-head">
        <div class="metric-icon blue">📰</div>
        <span class="metric-trend flat">total</span>
      </div>
      <div class="metric-value">${d.total_sources}</div>
      <div class="metric-label">Sources Analyzed</div>
    </div>
    <div class="metric">
      <div class="metric-head">
        <div class="metric-icon purple">📊</div>
        <span class="metric-trend ${d.avg_bias > 0.5 ? 'down' : d.avg_bias < 0.3 ? 'up' : 'flat'}">${(d.avg_bias * 100).toFixed(0)}%</span>
      </div>
      <div class="metric-value">${d.avg_bias.toFixed(2)}</div>
      <div class="metric-label">Average Bias Score</div>
    </div>`;
}

function renderTable(d) {
  let html = '<div class="section-title">Source Breakdown</div><div class="source-table">';

  d.articles.forEach((a, i) => {
    const pct = Math.max(5, Math.round(a.bias_score * 100));
    const cls = a.bias_label.toLowerCase();
    const sign = a.sentiment_compound >= 0 ? '+' : '';
    html += `
      <div class="source-row">
        <div class="source-dot ${cls}"></div>
        <span class="source-name">${esc(a.source_name)}</span>
        <div class="source-bar-wrap">
          <div class="source-bar ${cls}" style="width:0%" data-w="${pct}%"></div>
        </div>
        <span class="source-score">${sign}${a.sentiment_compound.toFixed(2)}</span>
        <span class="source-badge ${cls}">${a.bias_label}</span>
      </div>`;
  });

  html += '</div>';
  document.getElementById('sourceTable').innerHTML = html;

  requestAnimationFrame(() => {
    setTimeout(() => {
      document.querySelectorAll('.source-bar').forEach(b => { b.style.width = b.dataset.w; });
    }, 60);
  });
}

function renderKeywords(d) {
  let html = '';
  d.articles.forEach(a => {
    html += `<div class="kw-card">
      <div class="kw-card-title"><span>📰</span> ${esc(a.source_name)}</div>
      <div class="kw-section-label">Positive</div>
      <div class="kw-tags">${a.positive_keywords.length ? a.positive_keywords.map(w => `<span class="kw-tag pos">${esc(w)}</span>`).join('') : '<span class="kw-none">None detected</span>'}</div>
      <div class="kw-section-label">Negative</div>
      <div class="kw-tags">${a.negative_keywords.length ? a.negative_keywords.map(w => `<span class="kw-tag neg">${esc(w)}</span>`).join('') : '<span class="kw-none">None detected</span>'}</div>
    </div>`;
  });
  document.getElementById('deepContent').innerHTML = html;
}

function renderRadar(d) {
  const container = document.getElementById('nlpContent');
  container.innerHTML = '<div class="chart-wrap"><canvas id="radarChart" width="420" height="420"></canvas></div>';

  const canvas = document.getElementById('radarChart');
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2;
  const R = Math.min(cx, cy) - 50;
  const labels = ['Positive', 'Negative', 'Neutral', 'Bias'];
  const angles = labels.map((_, i) => (Math.PI * 2 * i) / labels.length - Math.PI / 2);
  const palette = ['#6366f1', '#22c55e', '#eab308', '#ef4444', '#a855f7'];

  // Grid
  for (let r = 0.2; r <= 1; r += 0.2) {
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    angles.forEach((a, i) => {
      const x = cx + Math.cos(a) * R * r;
      const y = cy + Math.sin(a) * R * r;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.stroke();
  }

  // Axes
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  angles.forEach(a => {
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R);
    ctx.stroke();
  });

  // Labels
  ctx.fillStyle = '#71717a';
  ctx.font = '12px Inter, sans-serif';
  ctx.textAlign = 'center';
  angles.forEach((a, i) => {
    ctx.fillText(labels[i], cx + Math.cos(a) * (R + 22), cy + Math.sin(a) * (R + 22) + 4);
  });

  // Data
  d.articles.forEach((art, idx) => {
    const vals = [art.sentiment_positive, art.sentiment_negative, art.sentiment_neutral, art.bias_score];
    const col = palette[idx % palette.length];

    ctx.beginPath();
    ctx.strokeStyle = col;
    ctx.lineWidth = 2;
    ctx.fillStyle = col + '18';
    vals.forEach((v, i) => {
      const x = cx + Math.cos(angles[i]) * R * v;
      const y = cy + Math.sin(angles[i]) * R * v;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    vals.forEach((v, i) => {
      ctx.beginPath();
      ctx.arc(cx + Math.cos(angles[i]) * R * v, cy + Math.sin(angles[i]) * R * v, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = col;
      ctx.fill();
    });
  });

  // Legend
  ctx.font = '11px Inter, sans-serif';
  let lx = 20;
  d.articles.forEach((a, i) => {
    const col = palette[i % palette.length];
    ctx.fillStyle = col;
    ctx.fillRect(lx, H - 18, 10, 10);
    ctx.fillStyle = '#71717a';
    ctx.textAlign = 'left';
    ctx.fillText(a.source_name, lx + 14, H - 9);
    lx += ctx.measureText(a.source_name).width + 30;
  });
}

/* ── History & Stats ──────────────────────────────────────────── */
async function loadHistory() {
  try {
    const r = await fetch(`${API}/api/history`);
    const data = await r.json();
    const c = document.getElementById('historyList');

    if (!data.length) {
      c.innerHTML = '<div class="empty" style="padding:0.8rem"><div style="font-size:1rem;opacity:0.3">📭</div><div style="font-size:0.7rem;color:var(--text-4)">No analyses yet</div></div>';
      return;
    }

    c.innerHTML = data.slice(0, 10).map(h => {
      const t = new Date(h.created_at);
      const ts = t.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      return `<div class="sidebar-item" onclick="loadAnalysis(${h.id})">
        <span class="sidebar-item-icon">📄</span>
        <span class="sidebar-item-text">${esc(h.topic.substring(0, 20))}</span>
        <span class="sidebar-item-meta">${ts}</span></div>`;
    }).join('');
  } catch (e) { console.error(e); }
}

async function loadAnalysis(id) {
  setLoading(true);
  try {
    const r = await fetch(`${API}/api/history/${id}`);
    if (!r.ok) throw new Error('Not found');
    currentAnalysis = await r.json();
    render(currentAnalysis);
    switchTab('scores');
  } catch (e) { alert('Failed to load'); }
  finally { setLoading(false); }
}

async function loadStats() {
  try {
    const r = await fetch(`${API}/api/stats`);
    const d = await r.json();
    document.getElementById('statTotal').textContent = d.total_analyses;
  } catch (e) { console.error(e); }
}

/* ── Util ─────────────────────────────────────────────────────── */
function setLoading(v) { document.getElementById('loadingOverlay').style.display = v ? 'flex' : 'none'; }

function shake(el) {
  el.style.animation = 'none';
  el.offsetHeight;
  el.style.animation = 'shk 0.35s ease';
  setTimeout(() => el.style.animation = '', 350);
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

const _s = document.createElement('style');
_s.textContent = '@keyframes shk{0%,100%{transform:translateX(0)}25%,75%{transform:translateX(-5px)}50%{transform:translateX(5px)}';
document.head.appendChild(_s);
