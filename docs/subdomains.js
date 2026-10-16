// Zoomable sunburst of the draft sub-domain tree (data/subdomain-map.json, from tools/subdomain_map.py).
// Rings: domain -> level-1 -> leaf -> question. Plain SVG, no chart library.
(function () {
  'use strict';
  const SCALES = ['0.1-1', '1-10', '10-100', '100-1000'];
  const SCALE_LABEL = { '0.1-1': '0.1–1 nm', '1-10': '1–10 nm', '10-100': '10–100 nm', '100-1000': '100–1000 nm' };
  const SHORT = { physics: '物理', chemistry: '化学', materials: '材料', biology: '生物' };
  const ABILITY = { perception: '感知', inference: '推理', design: '设计' };
  const R = 82, RINGS = 4, TAU = 2 * Math.PI, NS = 'http://www.w3.org/2000/svg';
  const DURATION = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 650;
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const cut = (s, n) => s.length > n ? s.slice(0, n - 1) + '…' : s;

  let DATA, mode = 'struct', root, nodes = [], focus, pinned, frame;

  fetch('data/subdomain-map.json').then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(map => {
    DATA = tree(map);
    stats(map);
    table();
    build();
    zoom(root, true);
    $('sd-mode-struct').addEventListener('click', () => setMode('struct'));
    $('sd-mode-count').addEventListener('click', () => setMode('count'));
  }).catch(() => { $('sd-error').hidden = false; });

  // ---- data -------------------------------------------------------------------------------------------------------
  function tree(map) {
    const leaf = Object.fromEntries(map.leaves.map(p => [p.leaf, p]));
    const pix = Object.fromEntries(map.pixels.map(p => [p.l1 + ' ' + p.scale, p]));
    $('sd-version').textContent = 'SUB-DOMAIN TREE · 草案 v' + map.taxonomy_version;
    return {
      kind: 'root', name: 'GeoBench', summary: map.summary,
      c: map.tree.map(d => ({
        kind: 'domain', id: d.id, dom: d.id, name: SHORT[d.id] || d.name, full: d.name, scheme: d.scheme,
        c: d.l1.map(o => ({
          kind: 'l1', id: o.id, dom: d.id, name: o.name, src: o.data_sources, sel: o.selection_criterion,
          scales: SCALES.map(s => [s, pix[o.id + ' ' + s].meaningful ? pix[o.id + ' ' + s].questions : null]),
          c: o.leaves.map(lf => {
            const p = leaf[lf.id];
            const qs = p.ids.map(id => ({ kind: 'q', id, dom: d.id, name: (map.titles[id] || [id])[0], ab: ABILITY[(map.titles[id] || [])[1]] || '' }));
            qs.forEach(q => { q.w = 1 / qs.length; });
            return { kind: 'leaf', id: lf.id, dom: d.id, name: lf.name, ex: lf.examples, cap: p.enumerated_estimate, q: qs };
          })
        }))
      }))
    };
  }
  const kids = d => d.c || (d.q && d.q.length ? d.q : null);
  const qOf = d => d.kind === 'q' ? [d] : d.kind === 'leaf' ? d.q : d.c.flatMap(qOf);
  const leavesOf = d => d.kind === 'leaf' ? [d] : d.kind === 'q' ? [] : d.c.flatMap(leavesOf);
  const weight = d => d.kind === 'q' ? (mode === 'struct' ? d.w : 1) : (d.kind === 'leaf' && !d.q.length && mode === 'struct' ? 1 : 0);

  // ---- layout -----------------------------------------------------------------------------------------------------
  function hierarchy(data, parent, depth) {
    const n = { data, parent, depth, children: null };
    const c = kids(data);
    if (c) n.children = c.map(x => hierarchy(x, n, depth + 1)).filter(x => x.value > 0);
    n.value = n.children ? n.children.reduce((s, x) => s + x.value, 0) : weight(data);
    return n;
  }
  function partition(n, x0, x1) {
    Object.assign(n, { x0, x1, y0: n.depth, y1: n.depth + 1 });
    let x = x0;
    (n.children || []).forEach(c => { const w = (x1 - x0) * c.value / n.value; partition(c, x, x + w); x += w; });
  }
  const ancestors = n => { const a = []; for (; n; n = n.parent) a.unshift(n); return a; };
  const descendants = n => [n].concat(...(n.children || []).map(descendants));

  // ---- drawing ----------------------------------------------------------------------------------------------------
  const pt = (a, r) => (r * Math.sin(a)).toFixed(2) + ',' + (-r * Math.cos(a)).toFixed(2);
  function arcPath(p) {
    const r0 = p.y0 * R, r1 = Math.max(r0, p.y1 * R - 1), span = p.x1 - p.x0;
    if (span <= 0) return '';
    if (span > TAU - 1e-6) {
      return `M${pt(0, r1)}A${r1},${r1} 0 1 1 ${pt(Math.PI, r1)}A${r1},${r1} 0 1 1 ${pt(0, r1)}` +
             `M${pt(0, r0)}A${r0},${r0} 0 1 0 ${pt(Math.PI, r0)}A${r0},${r0} 0 1 0 ${pt(0, r0)}Z`;
    }
    const large = span > Math.PI ? 1 : 0;
    return `M${pt(p.x0, r1)}A${r1},${r1} 0 ${large} 1 ${pt(p.x1, r1)}L${pt(p.x1, r0)}A${r0},${r0} 0 ${large} 0 ${pt(p.x0, r0)}Z`;
  }
  const arcVisible = p => p.y1 <= RINGS && p.y0 >= 1 && p.x1 > p.x0;
  const labelVisible = p => arcVisible(p) && (p.x1 - p.x0) * (p.y0 + p.y1) / 2 * R > 13;
  function labelTransform(p) {
    const x = (p.x0 + p.x1) / 2 * 180 / Math.PI, y = (p.y0 + p.y1) / 2 * R;
    return `rotate(${x - 90}) translate(${y},0) rotate(${x < 180 ? 0 : 180})`;
  }
  function labelText(d) {
    if (d.kind === 'domain') return d.name;
    if (d.kind === 'l1') return d.id + ' ' + cut(d.name, 6);
    if (d.kind === 'leaf') return d.id + ' ' + cut(d.name, 5);
    return d.id;
  }
  function opacity(d) {
    if (d.kind === 'domain') return 0.85;
    if (d.kind === 'l1') return qOf(d).length ? 0.62 : 0.2;
    if (d.kind === 'leaf') return d.q.length ? 0.42 : 0.13;
    return 0.26;
  }
  const el = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
  const pathTitle = n => ancestors(n).slice(1).map(a => a.data.kind === 'domain' ? a.data.name : a.data.id + ' ' + a.data.name).join(' › ');

  function build() {
    const svg = $('sd-svg');
    svg.textContent = '';
    root = hierarchy(DATA, null, 0);
    partition(root, 0, TAU);
    nodes = descendants(root).slice(1);
    const gPaths = el('g', {}), gLabels = el('g', { 'text-anchor': 'middle' });
    nodes.forEach(n => {
      n.cur = { x0: n.x0, x1: n.x1, y0: n.y0, y1: n.y1 };
      n.op = arcVisible(n.cur) ? 1 : 0;
      n.path = el('path', { class: n.data.kind, fill: `var(--d-${n.data.dom})` });
      const t = el('title', {}); t.textContent = pathTitle(n); n.path.appendChild(t);
      n.path.addEventListener('mouseenter', () => show(n));
      n.path.addEventListener('mouseleave', () => show(pinned || focus));
      n.path.addEventListener('click', () => { pinned = n; if (n.children) zoom(n); else show(n); });
      gPaths.appendChild(n.path);
      n.label = el('text', { dy: '0.35em', class: n.data.kind === 'domain' ? 't1' : n.data.kind === 'q' ? 'tq' : '' });
      n.label.textContent = labelText(n.data);
      gLabels.appendChild(n.label);
    });
    svg.append(gPaths, gLabels);
    const c = el('circle', { r: R, fill: 'var(--paper)', style: 'cursor:pointer' });
    c.addEventListener('click', () => { if (focus && focus.parent) { pinned = null; zoom(focus.parent); } });
    root.ct = el('text', { class: 'c-t', 'text-anchor': 'middle', dy: '-0.15em' });
    root.cs = el('text', { class: 'c-s', 'text-anchor': 'middle', dy: '1.5em' });
    svg.append(c, root.ct, root.cs);
    paint(1);
  }

  function paint(t) {
    nodes.forEach(n => {
      const p = n.cur, vis = arcVisible(p);
      const pathOp = n.op0 === undefined ? n.op : n.op0 + (n.op - n.op0) * t;
      n.path.setAttribute('d', pathOp > 0 || vis ? arcPath(p) : '');
      n.path.setAttribute('fill-opacity', (pathOp * opacity(n.data)).toFixed(3));
      n.path.style.pointerEvents = n.op ? 'auto' : 'none';
      const lo = n.lop0 === undefined ? n.lop : n.lop0 + (n.lop - n.lop0) * t;
      n.label.setAttribute('fill-opacity', (lo || 0).toFixed(3));
      if (lo > 0) n.label.setAttribute('transform', labelTransform(p));
    });
  }

  function zoom(p, now) {
    focus = p;
    nodes.forEach(n => {
      n.from = n.cur;
      n.to = {
        x0: Math.max(0, Math.min(1, (n.x0 - p.x0) / (p.x1 - p.x0))) * TAU,
        x1: Math.max(0, Math.min(1, (n.x1 - p.x0) / (p.x1 - p.x0))) * TAU,
        y0: Math.max(0, n.y0 - p.depth), y1: Math.max(0, n.y1 - p.depth)
      };
      n.op0 = n.op; n.op = arcVisible(n.to) ? 1 : 0;
      n.lop0 = n.lop === undefined ? 0 : n.lop; n.lop = labelVisible(n.to) ? 1 : 0;
    });
    cancelAnimationFrame(frame);
    const start = performance.now();
    const step = time => {
      const k = DURATION ? Math.min(1, (time - start) / DURATION) : 1;
      const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      nodes.forEach(n => {
        n.cur = { x0: n.from.x0 + (n.to.x0 - n.from.x0) * e, x1: n.from.x1 + (n.to.x1 - n.from.x1) * e,
                  y0: n.from.y0 + (n.to.y0 - n.from.y0) * e, y1: n.from.y1 + (n.to.y1 - n.from.y1) * e };
      });
      paint(e);
      if (k < 1) frame = requestAnimationFrame(step);
      else nodes.forEach(n => { n.op0 = undefined; n.lop0 = undefined; });
    };
    if (now) step(start + DURATION + 1); else frame = requestAnimationFrame(step);
    const d = p.data;
    root.ct.textContent = d.kind === 'root' ? 'GeoBench' : d.kind === 'domain' ? d.name : d.id;
    root.cs.textContent = p.parent ? '点击返回上一层' : qOf(d).length + ' 道题';
    crumbs();
    show(pinned || p);
  }

  function crumbs() {
    const box = $('sd-crumbs');
    box.textContent = '';
    ancestors(focus).forEach((a, i, all) => {
      if (i) { const s = document.createElement('span'); s.setAttribute('aria-hidden', 'true'); s.textContent = '›'; box.appendChild(s); }
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = a.data.kind === 'root' ? '全部' : a.data.kind === 'domain' ? a.data.name : a.data.id + ' ' + a.data.name;
      if (i === all.length - 1) b.setAttribute('aria-current', 'true');
      else b.addEventListener('click', () => { pinned = null; zoom(a); });
      box.appendChild(b);
    });
  }

  function setMode(m) {
    if (m === mode) return;
    mode = m;
    $('sd-mode-struct').setAttribute('aria-pressed', m === 'struct');
    $('sd-mode-count').setAttribute('aria-pressed', m === 'count');
    const keep = ancestors(focus).map(a => a.data);
    build();
    let p = root;
    for (const data of keep.slice(1)) { const next = (p.children || []).find(c => c.data === data); if (!next) break; p = next; }
    pinned = null;
    zoom(p, true);
  }

  function locate(id) {
    if (mode !== 'struct') setMode('struct');
    const n = nodes.find(x => x.data.id === id);
    if (!n) return;
    pinned = null;
    zoom(n.children ? n : n.parent);
    $('sd-svg').scrollIntoView({ behavior: DURATION ? 'smooth' : 'auto', block: 'center' });
  }

  // ---- side panel -------------------------------------------------------------------------------------------------
  const abilities = qs => ['感知', '推理', '设计'].map(k => `${k} ${qs.filter(q => q.ab === k).length}`).join(' · ');
  const nums = rows => '<div class="sd-nums">' + rows.map(([v, k]) => `<div><b>${v}</b><span>${k}</span></div>`).join('') + '</div>';
  const qList = qs => '<ul class="sd-qs">' + qs.map(q =>
    `<li><code><a href="cards.html#${q.id}">${q.id}</a></code><span>${esc(q.name)} <span class="muted">（${q.ab}）</span></span></li>`).join('') + '</ul>';
  const leafChip = (l, tag) => `<${tag} class="leaf${l.q.length ? '' : ' zero'}"${tag === 'button' ? ` type="button" data-locate="${l.id}"` : ''}><b>${l.id}</b> ${esc(l.name)} <i>${l.q.length}</i></${tag}>`;

  function show(n) {
    const d = n.data, qs = qOf(d), lv = leavesOf(d);
    let h;
    if (d.kind === 'root') {
      const l1 = d.c.flatMap(x => x.c);
      h = `<div class="k">ALL</div><h2>全部子领域</h2>` +
        nums([[d.c.length, '领域'], [l1.length, '第一层'], [lv.length, '叶子'], [qs.length, '现有题目']]) +
        `<p>有题的叶子 ${lv.filter(l => l.q.length).length} / ${lv.length}；完全没有题的第一层 ${l1.filter(o => !qOf(o).length).length} 个。</p>` +
        `<p class="muted">能力分布：${abilities(qs)}。点击任一领域放大。</p>`;
    } else if (d.kind === 'domain') {
      const empty = d.c.filter(o => !qOf(o).length);
      h = `<div class="k">DOMAIN</div><h2>${esc(d.full)}</h2><p class="muted">${esc(d.scheme)}</p>` +
        nums([[d.c.length, '第一层'], [lv.length, '叶子'], [qs.length, '题目'], [lv.filter(l => !l.q.length).length, '空叶子']]) +
        `<p>能力分布：${abilities(qs)}</p>` +
        (empty.length ? `<p class="muted">没有题的第一层：${empty.map(o => o.id + ' ' + esc(o.name)).join('、')}</p>` : '');
    } else if (d.kind === 'l1') {
      const cap = lv.reduce((s, l) => s + l.cap, 0);
      h = `<div class="k">${d.id} · 第一层子领域</div><h2>${esc(d.name)}</h2>` +
        nums([[qs.length, '题目'], [`${lv.filter(l => l.q.length).length}/${lv.length}`, '有题的叶子'], [cap ? cap.toLocaleString() : '—', '枚举估计容量']]) +
        '<div class="sd-scales">' + d.scales.map(([s, v]) => `<div>${SCALE_LABEL[s]}<span class="px ${v === null ? 'na' : v ? 'has' : 'zero'}">${v === null ? '—' : v}</span></div>`).join('') + '</div>' +
        `<p><b>数据来源</b>：${esc(d.src)}</p><p><b>结构选取准则（建议）</b>：${esc(d.sel)}</p>` +
        '<div class="chipset">' + d.c.map(l => leafChip(l, 'span')).join('') + '</div>';
    } else if (d.kind === 'leaf') {
      h = `<div class="k">${d.id} · 叶子子领域</div><h2>${esc(d.name)}</h2><p class="muted">例子：${esc(d.ex)}</p>` +
        nums([[qs.length, '题目'], [d.cap ? d.cap.toLocaleString() : '—', '枚举估计容量']]) +
        (qs.length ? `<p>能力分布：${abilities(qs)}</p>` + qList(qs) : '<p>还没有题。</p>');
    } else {
      const leaf = n.parent.data;
      h = `<div class="k">${d.id} · ${d.ab}</div><h2>${esc(d.name)}</h2><p class="muted">${leaf.id} ${esc(leaf.name)} · ${esc(n.parent.parent.data.name)}</p>` +
        `<p><a href="cards.html#${d.id}">在题目卡片页打开 ${d.id}</a></p>`;
    }
    $('sd-panel').innerHTML = h;
  }

  // ---- summary and table view -------------------------------------------------------------------------------------
  function stats(map) {
    const s = map.summary;
    $('sd-stats').innerHTML = [
      [s.level1, '个第一层子领域'], [s.leaves, `个叶子；${s.active_questions} 道题落在其中 ${s.leaves_with_questions} 个`],
      [s.meaningful_pixels, `个有意义的“第一层 × 尺度”像素；${s.pixels_with_questions} 个有题`],
      [s.empty_level1.length, '个第一层完全没有题'], ['≈' + s.mean_target_per_pixel, `道 / 像素（按 ${s.planning_total.toLocaleString()} 道平均）`]
    ].map(([v, k]) => `<div><b>${v}</b><span>${k}</span></div>`).join('');
  }

  function table() {
    $('sd-rows').innerHTML = DATA.c.map(d => `<div class="sd-dom"><h3><i class="sw" style="background:var(--d-${d.id})"></i>${esc(d.full)} <small>${esc(d.scheme)}</small></h3>` +
      d.c.map(o => {
        const n = qOf(o).length;
        return `<div class="l1${n ? '' : ' none'}"><div class="l1head"><button type="button" class="lid" data-locate="${o.id}" title="在旭日图中定位 ${o.id}">${o.id}</button>` +
          `<span>${esc(o.name)}</span><span class="ltot">${n} 道</span><span class="pxrow">` +
          o.scales.map(([s, v]) => `<span class="px ${v === null ? 'na' : v ? 'has' : 'zero'}" title="${SCALE_LABEL[s]}">${v === null ? '—' : v}</span>`).join('') +
          `</span></div><div class="chipset">${o.c.map(l => leafChip(l, 'button')).join('')}</div></div>`;
      }).join('') + '</div>').join('');
    $('sd-rows').addEventListener('click', e => { const b = e.target.closest('[data-locate]'); if (b) locate(b.dataset.locate); });
  }
})();
