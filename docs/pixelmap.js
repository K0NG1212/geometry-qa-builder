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

  fetch('data/subdomain-map.json').then(r => {
    if (!r.ok) throw Error('subdomain-map ' + r.status);
    return r.json();
  }).then(map => {
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
            html += '<div class="pix-cell na" title="这个尺度上没有这个子领域的题可做">·</div>';
            continue;
          }
          const n = pixel.questions || 0;
          const a = pixel.abilities || {};
          if (!n) {
            html += `<div class="pix-cell gap" title="${esc(l1.name)} · ${LABEL[bin]}：有意义但还没有题">缺</div>`;
            continue;
          }
          html += `<button type="button" class="pix-cell has" data-pixel="${esc(l1.id + '|' + bin)}" ` +
            `title="${esc(l1.name)} · ${LABEL[bin]}：${n} 道，点开看题号">` +
            `<strong>${n}</strong><small>${a.perception || 0}·${a.inference || 0}·${a.design || 0}</small></button>`;
        }
      }
      html += '</div></div>';
    }
    html += '<p class="caption">每格左上角是题数，下面是 感知·推断·设计 的拆分。' +
      '「缺」= 这个像素有意义但还没有题（教授看的就是这 20 格）；「·」= 这个子领域在这个尺度上没有题可做，不算缺口。' +
      '所有题都已通过程序核验与独立检查器，仍待人工审核。</p>' +
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
