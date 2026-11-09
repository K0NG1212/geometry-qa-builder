/* 读图指南 / Legend: every mark and abbreviation on the atlas, in one page.

   The 10th meeting asked for five things that are all the same thing -- saying what the reader is looking at:
   the ability colours (B1), a reason for every blank cell (B2), why the scale axis starts at 0.1 nm and stops
   at 1000 nm (B3), what the id letters and every abbreviation mean (B4), and what the classification is based
   on (B5). The content is hand-written in docs/content/legend.json and docs/content/gap-reasons.json, in both
   languages, because i18n.js matches whole strings and these sentences are too long to keep in a dictionary. */
(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));

  let en = true;
  try { en = (localStorage.getItem('geobench-lang') || 'en') === 'en'; } catch (err) { /* private mode */ }
  const pick = (zh, enText) => (en ? enText : zh);
  // the same bin labels the two maps print, so the table reads like the figure it explains
  const SCALE = {'0.1-1': '0.1–1 nm', '1-10': '1–10 nm', '10-100': '10–100 nm', '100-1000': '100–1000 nm'};
  const of = (obj, field) => (en ? obj[field + '_en'] : obj[field + '_zh']);

  Promise.all([
    fetch('content/legend.json').then((r) => { if (!r.ok) throw Error('legend ' + r.status); return r.json(); }),
    fetch('content/gap-reasons.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]).then(([L, gaps]) => {
    $('lg-status').textContent = pick(L.status_zh, L.status_en);

    // 01 abilities
    $('lg-ab-intro').textContent = pick(L.abilities.zh, L.abilities.en);
    $('lg-abilities').innerHTML = L.abilities.items.map((a) =>
      `<div class="${esc(a.letter.toLowerCase())}"><b>${esc(pick(a.zh, a.en))}</b>` +
      `<code>${esc(a.letter)} · ${esc(a.token)}</code>` +
      `<p>${esc(of(a, 'def'))}</p></div>`).join('');

    // 02 scales
    $('lg-scale-intro').textContent = pick(L.scales.zh, L.scales.en);
    $('lg-scale-kinds').innerHTML =
      '<table class="lg-table"><tbody>' + L.scales.kinds.map((k) =>
        `<tr><td class="term">${esc(pick(k.zh, k.en))}</td><td>${esc(of(k, 'def'))}</td></tr>`).join('') +
      `<tr><td class="term">${esc(pick('四个区间', 'The four bins'))}</td>` +
      `<td>${L.scales.bins.map(esc).join(' · ')}</td></tr></tbody></table>`;
    $('lg-scale-why').innerHTML = L.scales.boundaries.map((b) =>
      `<div class="lg-q"><b>${esc(of(b, 'q'))}</b><p>${esc(of(b, 'a'))}</p></div>`).join('');

    // 03 ids
    $('lg-ids').innerHTML = L.ids.systems.map((s) => {
      const parts = s.parts.map((p) =>
        `<tr><td class="term">${esc(of(p, 'pos'))}</td><td>${esc(of(p, 'detail'))}</td></tr>`).join('');
      const warn = s.caveats.map((c) => `<p class="lg-warn">${esc(pick(c.zh, c.en))}</p>`).join('');
      return `<div class="lg-id"><h3>${esc(of(s, 'name'))}</h3>` +
        `<p class="shape"><em>${esc(s.example)}</em> &nbsp; ${esc(of(s, 'shape'))}</p>` +
        `<table class="lg-table"><tbody>${parts}</tbody></table>${warn}</div>`;
    }).join('');

    // 04 taxonomy
    const t = L.taxonomy_basis;
    $('lg-taxonomy').innerHTML =
      `<div class="lg-q"><b>${esc(of(t, 'q'))}</b><p>${esc(of(t, 'a'))}</p></div>` +
      '<table class="lg-table" style="margin-top:14px"><thead><tr>' +
      `<th>${esc(pick('领域', 'Domain'))}</th><th>${esc(pick('依据', 'Basis'))}</th>` +
      '</tr></thead><tbody>' + t.schemes.map((s) =>
        `<tr><td class="term">${esc(pick(s.zh, s.en))}</td><td>${esc(of(s, 'basis'))}</td></tr>`).join('') +
      '</tbody></table>' +
      `<p style="margin:16px 0 4px;font-size:13px"><b>${esc(pick('归属规则', 'Filing rules'))}</b></p>` +
      '<ol style="font-size:13px;line-height:1.75;margin:0;padding-left:20px">' +
      (en ? t.rules_en : t.rules_zh).map((r) => `<li>${esc(r)}</li>`).join('') + '</ol>' +
      `<p class="lg-warn">${esc(of(t, 'caveat'))}</p>`;

    // 05 blanks
    if (gaps) {
      const c = gaps.counts;
      $('lg-gap-intro').innerHTML = esc(en
        ? `The detailed map has ${c.na + c.gap} blank cells. ${c.gap} of them are meaningful cells with no ` +
          `question yet -- the real gaps -- and ${c.na} lie outside the scales the subdomain reaches. Every ` +
          'one carries a reason, listed in full below.'
        : `细坐标图上有 ${c.na + c.gap} 个空白格。其中 ${c.gap} 个是「有意义但还没出题」—— 真正的缺口；` +
          `另外 ${c.na} 个在这个子领域达不到的尺度上。每一格都写了理由，下面是全部。`) +
        `<br><span class="lg-note">${esc(pick(gaps.status_zh, gaps.status_en))}</span>`;
      $('lg-gap-kinds').innerHTML =
        '<table class="lg-table"><thead><tr>' +
        `<th>${esc(pick('记号', 'Mark'))}</th><th>${esc(pick('哪一种', 'Kind'))}</th>` +
        `<th>${esc(pick('意思', 'Meaning'))}</th><th>${esc(pick('格数', 'Cells'))}</th>` +
        '</tr></thead><tbody>' +
        Object.entries(gaps.kinds).map(([id, k]) =>
          `<tr><td class="term" style="color:var(--gap-${esc(id)});font-size:15px">${esc(k.mark)}</td>` +
          `<td class="term" style="color:var(--gap-${esc(id)})">${esc(pick(k.zh, k.en))}</td>` +
          `<td>${esc(of(k, 'gloss'))}</td><td>${esc(c.by_kind[id] || 0)}</td></tr>`).join('') +
        '</tbody></table>';
      const rows = Object.entries(gaps.pixels).sort((a, b) => a[0].localeCompare(b[0]));
      $('lg-gap-table').innerHTML =
        '<table class="lg-table" style="margin-top:16px"><thead><tr>' +
        (en ? '<th>Cell</th><th>Subdomain</th><th>Scale</th><th>Kind</th><th>Reason</th>'
            : '<th>格</th><th>子领域</th><th>尺度</th><th>哪一种</th><th>理由</th>') +
        '</tr></thead><tbody>' + rows.map(([key, r]) =>
          `<tr><td class="term">${esc(key)}</td><td class="term">${esc(r.name)}</td>` +
          `<td class="term">${esc(SCALE[r.scale] || r.scale + ' nm')}</td>` +
          `<td class="term" style="color:var(--gap-${esc(r.kind)})">` +
          `${esc(pick(gaps.kinds[r.kind].zh, gaps.kinds[r.kind].en))}</td>` +
          `<td>${esc(en ? r.en : r.zh)}</td></tr>`).join('') + '</tbody></table>';
    } else {
      $('lg-gap-intro').textContent = pick('空白格理由暂时无法载入。', 'The reasons for the blank cells could not be loaded.');
    }

    // 06 abbreviations
    $('lg-abbr').innerHTML = L.abbreviations.map((g) =>
      `<h3 style="font-size:14px;margin:20px 0 6px">${esc(of(g, 'group'))}</h3>` +
      '<table class="lg-table"><tbody>' + g.items.map((i) =>
        `<tr><td class="term">${esc(i.t)}</td><td>${esc(pick(i.zh, i.en))}</td></tr>`).join('') +
      '</tbody></table>').join('');
  }).catch((err) => {
    $('lg-error').hidden = false;
    console.error('Legend load failed', err);
  });
})();
