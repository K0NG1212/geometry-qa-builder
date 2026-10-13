'use strict';
// Quizlet-style question cards (sixth advisor meeting). Data: data/cards.json from tools/export_cards.py.
(() => {
  const $ = id => document.getElementById(id);
  const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const ABILITY = {perception: '感知', inference: '推断', design: '设计'};
  const DOMAIN = {quantum: '量子', chemistry: '化学', materials: '材料', biology: '生物'};
  const SCALE = {'0.1-1': '0.1–1 nm', '1-10': '1–10 nm', '10-100': '10–100 nm', '100-1000': '100–1000 nm'};
  const FORMAT = {choice: '四选一', open: '非四选一（旧题）'};
  const store = {
    get(k, d) { try { const v = localStorage.getItem('geobench-cards-' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem('geobench-cards-' + k, JSON.stringify(v)); } catch (e) { /* storage unavailable */ } }
  };
  let all = [], shown = [], pos = 0, subNames = {};
  let answers = store.get('answers', {});        // id -> chosen label
  let flags = store.get('flags', {});            // id -> note
  let revealed = new Set();
  let autoTimer = null;

  function boxes(field, values, labels) {
    const el = $('f-' + field);
    el.insertAdjacentHTML('beforeend', values.map(v =>
      `<label><input type="checkbox" value="${esc(v)}" checked data-f="${field}">${esc(labels[v])}<small data-n="${field}:${esc(v)}"></small></label>`).join(''));
  }
  function checked(field) { return new Set([...document.querySelectorAll(`input[data-f="${field}"]:checked`)].map(i => i.value)); }

  function apply(keepId) {
    const ab = checked('ability'), dm = checked('domain'), sc = checked('scale'), fm = checked('format');
    const q = $('f-search').value.trim().toLowerCase(), sub = $('f-sub').value, onlyFlag = $('f-flagged').checked;
    const order = shown.length && $('shuffle').dataset.on === '1' ? new Map(shown.map((c, i) => [c.id, i])) : null;
    shown = all.filter(c => ab.has(c.ability) && dm.has(c.domain) && sc.has(c.scale) && fm.has(c.format) &&
      (!sub || c.subdomain === sub) && (!onlyFlag || flags[c.id] !== undefined) &&
      (!q || c.id.toLowerCase().includes(q) || c.title.toLowerCase().includes(q)));
    if (order) shown.sort((a, b) => (order.get(a.id) ?? 1e9) - (order.get(b.id) ?? 1e9));
    for (const field of ['ability', 'domain', 'scale', 'format']) {
      document.querySelectorAll(`[data-n^="${field}:"]`).forEach(el => {
        const v = el.dataset.n.split(':')[1];
        el.textContent = all.filter(c => c[field] === v).length;
      });
    }
    const i = keepId ? shown.findIndex(c => c.id === keepId) : -1;
    pos = i >= 0 ? i : 0;
    render();
  }

  function score() {
    const ids = Object.keys(answers).filter(id => all.some(c => c.id === id && c.format === 'choice'));
    const right = ids.filter(id => all.find(c => c.id === id).correct === answers[id]).length;
    $('score').textContent = ids.length ? `已答 ${ids.length} · 答对 ${right}` : '';
    $('flag-note').textContent = `已标记 ${Object.keys(flags).length} 道。标记只存在这台电脑的浏览器里。`;
  }

  function fileHtml(f, i) {
    const dl = f.url ? `<a class="dl" href="${esc(f.url)}" download>下载</a>` : '';
    const pv = f.url || f.text ? `<button type="button" data-preview="${i}">预览</button>` : '';
    return `<div class="file"><div class="row"><b>${esc(f.name)}</b><small>${esc(f.note || '')}</small>${pv}${dl}</div><div data-slot="${i}"></div></div>`;
  }

  function render() {
    clearTimeout(autoTimer);
    $('count').textContent = shown.length ? `第 ${pos + 1} / ${shown.length} 张（共 ${all.length} 张）` : `0 / ${all.length} 张`;
    $('bar').style.width = shown.length ? `${100 * (pos + 1) / shown.length}%` : '0';
    $('prev').disabled = pos <= 0; $('next').disabled = pos >= shown.length - 1;
    score();
    const c = shown[pos];
    if (!c) { $('card').innerHTML = '<div class="empty-state">没有符合筛选条件的题目。<br>放宽左侧的勾选或清除筛选。</div>'; return; }
    if (location.hash.slice(1) !== c.id) history.replaceState(null, '', '#' + c.id);
    const chosen = answers[c.id], open = revealed.has(c.id) || (c.format === 'choice' && chosen);
    const chips = [`<span class="chip">${esc(c.id)}</span>`, `<span class="chip ab-${c.ability}">${ABILITY[c.ability]}</span>`,
      `<span class="chip">${DOMAIN[c.domain]}</span>`, `<span class="chip">${SCALE[c.scale]}</span>`,
      `<span class="chip">${esc(c.subdomain)} ${esc(subNames[c.subdomain] || '')}</span>`,
      c.format === 'open' ? '<span class="chip warn">非四选一的旧题</span>' : '',
      flags[c.id] !== undefined ? '<span class="chip warn">已标记问题</span>' : ''].join('');
    let opts = '';
    if (c.format === 'choice') {
      opts = '<div class="options" role="group" aria-label="选项">' + c.options.map(o => {
        let cls = '';
        if (chosen) cls = o.label === c.correct ? ' correct' : (o.label === chosen ? ' wrong' : '');
        return `<button type="button" class="opt${cls}" data-label="${o.label}" ${chosen ? 'disabled' : ''}><span class="lab">${o.label}</span><span class="val">${esc(o.value)}${o.unit ? ' ' + esc(o.unit) : ''}</span></button>`;
      }).join('') + '</div>';
    } else {
      opts = '<p class="chip warn" style="display:inline-block;margin-top:14px">这道旧题还没有四选一版本，原为数值或文字作答。</p>';
    }
    let rev = '';
    if (open) {
      if (c.format === 'choice') {
        const verdict = chosen ? (chosen === c.correct ? '<div class="verdict ok">✓ 答对了</div>' : `<div class="verdict no">✗ 选了 ${chosen}，正确答案是 ${c.correct}</div>`)
                               : `<div class="verdict">正确答案：${c.correct}</div>`;
        const why = c.options.map(o => {
          const r = c.reasons[o.label] || {};
          return `<div><span class="${r.correct ? 'is-right' : ''}">${o.label}</span><span>${r.correct ? '<b>正确。</b>' : ''}${esc(r.reason || '')}</span></div>`;
        }).join('');
        const num = c.numeric ? `<div>数值作答版：${esc(c.numeric.value)} ${esc(c.numeric.unit || '')}（容差 ±${esc(c.numeric.tolerance)}）</div>` : '';
        rev = `<div class="reveal">${verdict}<div class="why">${why}</div><div class="meta">${num}${meta(c)}</div></div>`;
      } else {
        rev = `<div class="reveal"><div class="verdict">参考答案</div><div class="qtext">${esc(c.answer)}</div><div class="meta"><div>评分：${esc(c.rubric)}</div>${meta(c)}</div></div>`;
      }
    }
    const flagged = flags[c.id] !== undefined;
    $('card').innerHTML = `<div class="chips">${chips}</div><h2>${esc(c.title)}</h2>
      <div class="qtext">${esc(c.question)}</div>
      ${c.files.length ? `<div class="files">${c.files.map(fileHtml).join('')}</div>` : ''}
      ${opts}${rev}
      <div class="actions">
        ${open ? '' : '<button type="button" class="primary" id="show">显示答案</button>'}
        <button type="button" id="flag">${flagged ? '编辑问题标记' : '标记有问题'}</button>
        ${flagged ? '<span class="flagged-tag">已标记：' + esc(flags[c.id] || '（无说明）') + '</span>' : ''}
      </div>
      <div class="flag-box" id="flag-box" hidden><label for="flag-text">这道题有什么问题？（只存在本机浏览器）</label>
        <textarea id="flag-text">${esc(flags[c.id] || '')}</textarea>
        <div class="actions" style="margin-top:0"><button type="button" class="primary" id="flag-save">保存标记</button>${flagged ? '<button type="button" id="flag-del">取消标记</button>' : ''}</div></div>`;
  }

  function meta(c) {
    const src = /^https?:/.test(c.source) ? `<a href="${esc(c.source)}" target="_blank" rel="noopener">${esc(c.source)}</a>` : esc(c.source);
    return `<div>考点：${esc(c.objective)}</div><div>尺度：${esc(c.size)}</div><div>来源：${src}</div>
      <div>版本：${esc(c.version)} · 题型族 ${esc(c.family)}</div>
      <div><a href="index.html?qa=${encodeURIComponent(c.id)}#questions">在问题池打开完整详情</a>${c.trace ? ` · <a href="${esc(c.trace)}">题型工作台记录（选项核验、独立检查）</a>` : ''}</div>`;
  }

  function choose(label) {
    const c = shown[pos];
    if (!c || c.format !== 'choice' || answers[c.id]) return;
    answers[c.id] = label; store.set('answers', answers);
    render();
    if ($('auto').checked && pos < shown.length - 1) autoTimer = setTimeout(() => go(1), 2500);
  }
  function go(d) { const n = pos + d; if (n >= 0 && n < shown.length) { pos = n; render(); window.scrollTo({top: 0}); } }

  async function preview(i, btn) {
    const c = shown[pos], f = c.files[i], slot = document.querySelector(`[data-slot="${i}"]`);
    if (slot.innerHTML) { slot.innerHTML = ''; btn.textContent = '预览'; return; }
    let text = f.text;
    if (!text) {
      try { const r = await fetch(f.url); if (!r.ok) throw new Error(r.status); text = await r.text(); }
      catch (e) { slot.innerHTML = '<p class="note">读取失败，请用“下载”打开。</p>'; return; }
    }
    const lines = text.split('\n'), head = lines.slice(0, 80).join('\n');
    slot.innerHTML = `<pre>${esc(head)}</pre>` + (lines.length > 80 ? `<small>只显示前 80 行，共 ${lines.length} 行；完整内容请下载。</small>` : '');
    btn.textContent = '收起';
  }

  document.addEventListener('click', e => {
    const t = e.target.closest('button'); if (!t) return;
    if (t.dataset.label) choose(t.dataset.label);
    else if (t.dataset.preview !== undefined) preview(+t.dataset.preview, t);
    else if (t.id === 'show') { revealed.add(shown[pos].id); render(); }
    else if (t.id === 'flag') { const b = $('flag-box'); b.hidden = !b.hidden; if (!b.hidden) $('flag-text').focus(); }
    else if (t.id === 'flag-save') { flags[shown[pos].id] = $('flag-text').value.trim(); store.set('flags', flags); render(); }
    else if (t.id === 'flag-del') { delete flags[shown[pos].id]; store.set('flags', flags); render(); }
  });
  $('prev').addEventListener('click', () => go(-1));
  $('next').addEventListener('click', () => go(1));
  $('shuffle').addEventListener('click', e => {
    const b = e.currentTarget, id = shown[pos]?.id;
    if (b.dataset.on === '1') { b.dataset.on = '0'; b.textContent = '打乱顺序'; shown = []; apply(id); return; }
    b.dataset.on = '1'; b.textContent = '恢复顺序';
    for (let i = shown.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [shown[i], shown[j]] = [shown[j], shown[i]]; }
    pos = 0; render();
  });
  $('clear-score').addEventListener('click', () => { answers = {}; revealed.clear(); store.set('answers', answers); render(); });
  $('export-flags').addEventListener('click', () => {
    const rows = Object.entries(flags).map(([id, note]) => { const c = all.find(x => x.id === id) || {}; return {id, title: c.title, note}; });
    const blob = new Blob([JSON.stringify({exported: new Date().toISOString(), flags: rows}, null, 2)], {type: 'application/json'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'geobench-card-flags.json'; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  $('reset').addEventListener('click', () => {
    document.querySelectorAll('input[data-f]').forEach(i => { i.checked = true; });
    $('f-search').value = ''; $('f-sub').value = ''; $('f-flagged').checked = false; apply();
  });
  $('filter-toggle').addEventListener('click', () => {
    const f = $('filters'), open = f.dataset.collapsed === 'true';
    f.dataset.collapsed = open ? 'false' : 'true'; $('filter-toggle').setAttribute('aria-expanded', String(open));
  });
  $('filters').addEventListener('change', () => apply(shown[pos]?.id));
  $('f-search').addEventListener('input', () => apply(shown[pos]?.id));
  $('auto').checked = store.get('auto', false);
  $('auto').addEventListener('change', () => store.set('auto', $('auto').checked));
  document.addEventListener('keydown', e => {
    if (e.target.closest && e.target.closest('input,textarea,select')) return;
    const k = e.key.toUpperCase();
    if (e.key === 'ArrowLeft') go(-1);
    else if (e.key === 'ArrowRight') go(1);
    else if ('1234'.includes(k) && k.length === 1) choose('ABCD'[+k - 1]);
    else if ('ABCD'.includes(k) && k.length === 1) choose(k);
    else if (e.key === ' ') { e.preventDefault(); if (shown[pos]) { revealed.add(shown[pos].id); render(); } }
    else if (k === 'F') $('flag')?.click();
  });

  fetch('data/cards.json').then(r => r.json()).then(d => {
    all = d.cards; subNames = d.subdomains;
    boxes('ability', ['perception', 'inference', 'design'], ABILITY);
    boxes('domain', ['quantum', 'chemistry', 'materials', 'biology'], DOMAIN);
    boxes('scale', Object.keys(SCALE), SCALE);
    boxes('format', ['choice', 'open'], FORMAT);
    $('f-sub').insertAdjacentHTML('beforeend', Object.entries(subNames).map(([k, v]) => {
      const n = all.filter(c => c.subdomain === k).length;
      return `<option value="${esc(k)}">${esc(k)} ${esc(v)}（${n}）</option>`;
    }).join(''));
    apply(location.hash.slice(1) || null);
  }).catch(() => { $('card').innerHTML = '<div class="empty-state">题目数据读取失败，请刷新页面。</div>'; });
})();
