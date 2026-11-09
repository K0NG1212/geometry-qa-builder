/* The detailed coordinate system: level-1 subdomain x reasoning scale, one cell per pixel.

   The 4x4 map above is the summary the project started from; with 871 questions it says little beyond
   "chemistry has a lot". This map is the one the coverage is actually planned against: 32 level-1 subdomains
   times 4 reasoning scales, with the cells that cannot hold a question (a scale the subdomain does not reach)
   marked as such, so an empty cell is a real gap and not an artefact of the grid. Data: subdomain_map.py.
   Clicking a cell lists its questions; clicking a question id opens the same detail dialog as the pool. */
(() => {
  const host = document.getElementById('pixelmap');
  if (!host) return;
  const BINS = ['0.1-1', '1-10', '10-100', '100-1000'];
  const LABEL = {'0.1-1': '0.1–1 nm', '1-10': '1–10 nm', '10-100': '10–100 nm', '100-1000': '100–1000 nm'};
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

  Promise.all([
    fetch('data/subdomain-map.json').then(r => {
      if (!r.ok) throw Error('subdomain-map ' + r.status);
      return r.json();
    }),
    // Hand-written, and allowed to be missing: the map still renders, the cells just lose their reason.
    fetch('content/gap-reasons.json').then(r => (r.ok ? r.json() : null)).catch(() => null),
  ]).then(([map, reasons]) => {
    const KINDS = (reasons && reasons.kinds) || {};
    const WHY = (reasons && reasons.pixels) || {};
    const at = {};
    map.pixels.forEach(p => { at[p.l1 + '|' + p.scale] = p; });
    const s = map.summary;
    // i18n.js matches whole strings, and this sentence is built from numbers, so it is written here in both
    let en = true;
    try { en = (localStorage.getItem('geobench-lang') || 'en') === 'en'; } catch (err) { /* private mode */ }
    const summary = en
      ? `<b>${s.pixels_with_questions} / ${s.meaningful_pixels}</b> meaningful pixels hold questions · ` +
        `<b>${s.empty_meaningful_pixels}</b> still empty · level-2 subdomains (leaves) ${s.leaves_with_questions} / ${s.leaves} · ` +
        `${s.active_questions} questions in all. A pixel is one level-1 subdomain at one reasoning scale.`
      : `<b>${s.pixels_with_questions} / ${s.meaningful_pixels}</b> 个有意义像素有题 · ` +
        `<b>${s.empty_meaningful_pixels}</b> 个空缺 · 二级子领域（叶子） ${s.leaves_with_questions} / ${s.leaves} · ` +
        `共 ${s.active_questions} 道。像素 = 一级子领域 × 解题推理尺度。`;
    const kindOf = (key) => (WHY[key] && WHY[key].kind) || null;
    const reasonOf = (key) => {
      const r = WHY[key];
      return r ? (en ? r.en : r.zh) : null;
    };
    const kindName = (kind) => {
      const k = KINDS[kind];
      return k ? (en ? k.en : k.zh) : kind;
    };
    const blank = (l1, bin, name, which) => {
      const key = l1 + '|' + bin;
      const kind = kindOf(key);
      const why = reasonOf(key);
      const head = `${name} · ${LABEL[bin]}`;
      const title = kind
        ? (en ? `${head} — ${kindName(kind)}: ${why}` : `${head} — ${kindName(kind)}：${why}`)
        : (which === 'na'
            ? (en ? `${head}: no question of this subdomain exists at this scale`
                  : `${head}：这个尺度上没有这个子领域的题可做`)
            : (en ? `${head}: meaningful, but no question yet` : `${head}：有意义但还没有题`));
      const mark = (kind && KINDS[kind] && KINDS[kind].mark) || (which === 'na' ? '·' : '缺');
      return `<div class="pix-cell ${which}"${kind ? ` data-kind="${esc(kind)}"` : ''} ` +
        `title="${esc(title)}">${esc(mark)}</div>`;
    };
    const kindKey = Object.keys(KINDS).length
      ? '<div class="gap-key">' + Object.entries(KINDS).map(([id, k]) =>
          `<b title="${esc(en ? k.gloss_en : k.gloss_zh)}"><em style="color:var(--gap-${id})">${esc(k.mark)}</em>` +
          `${esc(en ? k.en : k.zh)}</b>`).join('') + '</div>'
      : '';
    let html = '<p class="pix-summary">' + summary +
      '<a class="text-link" href="subdomains.html">旭日图与二级子领域 ↗</a></p>';

    for (const domain of map.tree) {
      html += `<div class="pix-domain"><h3>${esc(domain.name)}</h3>`;
      html += '<div class="pix-grid"><div class="pix-head"></div>' +
        BINS.map(b => `<div class="pix-head">${LABEL[b]}</div>`).join('');
      for (const l1 of domain.l1 || []) {
        const title = [l1.data_sources, l1.selection_criterion].filter(Boolean).join('；');
        html += `<div class="pix-label" title="${esc(title)}"><b>${esc(l1.id)}</b> ${esc(l1.name)}</div>`;
        for (const bin of BINS) {
          const pixel = at[l1.id + '|' + bin];
          if (!pixel || !pixel.meaningful) {
            html += blank(l1.id, bin, l1.name, 'na');
            continue;
          }
          const n = pixel.questions || 0;
          const a = pixel.abilities || {};
          if (!n) {
            html += blank(l1.id, bin, l1.name, 'gap');
            continue;
          }
          const parts = [['p', a.perception || 0], ['i', a.inference || 0], ['d', a.design || 0]];
          const split = parts.map(([cls, v]) => (v ? `<span class="${cls}" style="flex:${v}"></span>` : '')).join('');
          const names = en ? ['Perception', 'Inference', 'Design'] : ['感知', '推断', '设计'];
          const hover = parts.map(([, v], i) => `${names[i]} ${v}`).join(en ? ', ' : '、');
          html += `<button type="button" class="pix-cell has" data-pixel="${esc(l1.id + '|' + bin)}" ` +
            `title="${esc(l1.name)} · ${LABEL[bin]}：${n} 道，点开看题号">` +
            `<strong>${n}</strong><small title="${esc(hover)}">` +
            parts.map(([cls, v], i) => `<b class="ab-${cls}" title="${esc(names[i] + ' ' + v)}">${v}</b>`)
              .join('<em>·</em>') +
            `</small><span class="pix-split" title="${esc(hover)}">${split}</span></button>`;
        }
      }
      html += '</div></div>';
    }
    const rows = Object.entries(WHY).sort((x, y) => x[0].localeCompare(y[0]));
    const table = rows.length
      ? '<details class="gap-reasons"><summary>' +
        (en ? `Why each of the ${rows.length} blank cells is blank (${reasons.counts.gap} real gaps, ` +
              `${reasons.counts.na} outside the subdomain\u2019s scales)`
            : `${rows.length} 个空白格，逐格的理由（其中真正的缺口 ${reasons.counts.gap} 个，` +
              `尺度之外 ${reasons.counts.na} 个）`) +
        '</summary><p class="caption">' + esc(en ? reasons.status_en : reasons.status_zh) + '</p>' +
        '<table><thead><tr>' +
        (en ? '<th>Cell</th><th>Subdomain</th><th>Scale</th><th>Kind</th><th>Reason</th>'
            : '<th>格</th><th>子领域</th><th>尺度</th><th>哪一种</th><th>理由</th>') +
        '</tr></thead><tbody>' +
        rows.map(([key, r]) => `<tr><td class="kind">${esc(key)}</td><td>${esc(r.name)}</td>` +
          `<td class="kind">${LABEL[r.scale]}</td>` +
          `<td class="kind" style="color:var(--gap-${esc(r.kind)})">${esc(kindName(r.kind))}</td>` +
          `<td>${esc(en ? r.en : r.zh)}</td></tr>`).join('') +
        '</tbody></table></details>'
      : '';
    html += '<p class="caption">每格左上角是题数，下面是 感知·推断·设计 的拆分（三个数字与下面那条比例条用全站统一的三种颜色，悬停显示能力名）。' +
      '空白格每一格都写了理由：悬停看一句话，下面的表格列出全部。' +
      '所有题都已通过程序核验与独立检查器，仍待人工审核。</p>' +
      kindKey + table +
      '<div id="pixel-list" hidden></div>';
    host.innerHTML = html;

    host.addEventListener('click', event => {
      const cell = event.target.closest('[data-pixel]');
      if (!cell) return;
      const pixel = at[cell.dataset.pixel];
      const list = document.getElementById('pixel-list');
      const open = cell.classList.contains('open');
      host.querySelectorAll('.pix-cell.open').forEach(c => c.classList.remove('open'));
      if (open) { list.hidden = true; return; }
      cell.classList.add('open');
      list.hidden = false;
      // Three nodes, not one string: i18n.js translates a whole text node, so the subdomain name has to sit on
      // its own for the dictionary to find it, and the count on its own for the plural rule to rewrite it.
      list.innerHTML = `<p><b>${esc(pixel.name)}</b> · ${LABEL[pixel.scale]} · ` +
        `<span>${pixel.questions} 道（点题号看完整题目、附件与来源）</span></p>` +
        (pixel.ids || []).map(id => `<button type="button" class="text-button" data-question="${esc(id)}">${esc(id)}</button>`).join(' ');
      list.scrollIntoView({block: 'nearest', behavior: 'smooth'});
    });
  }).catch(err => {
    host.innerHTML = '<p class="caption">子领域像素图暂时无法载入。</p>';
    console.error(err);
  });
})();
