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
    fetch('content/sources.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
    fetch('data/source-coverage.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
    fetch('content/related-work.json').then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]).then(([L, gaps, S, cov, RW]) => {
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

    // 07 sources: why each one, and how much of its structure space the pool samples (C1)
    if (S && cov) {
      const n = (v) => (v == null ? '—' : v.toLocaleString('en-US'));
      $('lg-src-intro').innerHTML = esc(of(S, 'why_strata')) +
        `<br><span class="lg-note">${esc(pick(S.status_zh, S.status_en))}</span>`;

      const ec = cov.rcsb_pdb.ec_strata;
      $('lg-src-strata').innerHTML =
        `<h3 style="font-size:14px;margin:22px 0 6px">${esc(pick('逐层覆盖', 'Coverage by stratum'))}</h3>` +
        '<table class="lg-table"><thead><tr>' +
        `<th>${esc(pick('分层口径', 'Stratum'))}</th><th>${esc(pick('源里有', 'In the source'))}</th>` +
        `<th>${esc(pick('我们用到', 'Ours'))}</th></tr></thead><tbody>` +
        ec.map((s) => `<tr><td class="term"${s.ours ? '' : ' style="color:var(--gap-uncollected)"'}>` +
          `EC ${esc(s.ec)} ${esc(pick(s.zh, s.en))}</td><td>${n(s.in_source)}</td>` +
          `<td${s.ours ? '' : ' style="color:var(--gap-uncollected);font-weight:600"'}>${s.ours}` +
          `${s.ours ? '' : esc(pick('　空缺', '　empty'))}</td></tr>`).join('') +
        `<tr><td class="term">${esc(pick('PDB 分辨率 ≤ 2.0 Å', 'PDB entries at 2.0 A or better'))}</td>` +
        `<td>${n(cov.rcsb_pdb.resolution.known)} ${esc(pick('个用到的条目', 'entries used'))}</td>` +
        `<td>${cov.rcsb_pdb.resolution.at_or_below_2A}</td></tr>` +
        `<tr><td class="term">${esc(pick('COD 空间群', 'COD space groups'))}</td>` +
        `<td>${n(cov.cod.space_groups_possible)}</td><td>${cov.cod.space_groups_used}</td></tr>` +
        `<tr><td class="term">${esc(pick('QM7-X 分子式', 'QM7-X formulae'))}</td>` +
        `<td>${n(cov.qm7x.formulae_in_source)}</td><td>${cov.qm7x.distinct_molecules}</td></tr>` +
        `<tr><td class="term">${esc(pick('SAMPL9 主体', 'SAMPL9 hosts'))}</td>` +
        `<td>${cov.sampl9.hosts_in_challenge}</td><td>${cov.sampl9.hosts_used}</td></tr>` +
        '</tbody></table>';

      const counts = cov.questions_by_source;
      const distinct = {rcsb_pdb: [cov.rcsb_pdb.distinct_entries, '个 PDB 条目', 'PDB entries'],
                        cod: [cov.cod.cif_files, '个 CIF', 'CIF files'],
                        qm7x: [cov.qm7x.distinct_molecules, '个分子', 'molecules'],
                        sampl9: [cov.sampl9.hosts_used, '个主体', 'hosts'],
                        papers: [cov.papers.distinct_labels, '个来源标识', 'source labels']};
      $('lg-src-list').innerHTML = S.sources.map((s) => {
        const d = distinct[s.key] || [];
        const head = en
          ? `${counts[s.key] || 0} questions · ${d[0]} ${d[2] || ''}`
          : `${counts[s.key] || 0} 道题 · ${d[0]} ${d[1] || ''}`;
        return `<div class="lg-src"><h4>${esc(s.name)}</h4><p class="n">${esc(head)}</p><dl>` +
          [['为什么选它', 'Why this one', 'why'], ['覆盖什么', 'Covers', 'covers'],
           ['不覆盖什么', 'Does not cover', 'misses'], ['替代与为什么没用', 'Alternatives', 'alternatives']]
            .map(([zh, enLabel, field]) =>
              `<dt>${esc(pick(zh, enLabel))}</dt><dd>${esc(of(s, field))}</dd>`).join('') +
          '</dl></div>';
      }).join('');

      $('lg-src-gaps').innerHTML = S.gaps.map((g) =>
        `<p class="lg-gap">${esc(pick(g.zh, g.en))}</p>`).join('');
    }

    // 08 related work: what the comparable benchmarks run as baselines (D1)
    if (RW) {
      const HUMAN = {yes: ['有', 'Yes'], not_stated: ['摘要未写', 'Not stated'],
                     unchecked: ['未核对', 'Not checked']};
      $('lg-rw-intro').innerHTML = esc(of(RW, 'method')) +
        `<br><span class="lg-note">${esc(pick(RW.status_zh, RW.status_en))}</span>`;
      $('lg-rw-table').innerHTML =
        '<table class="lg-table"><thead><tr>' +
        (en ? '<th>ID</th><th>Work</th><th>Scale</th><th>Baselines</th><th>Human</th><th>How reported</th>'
            : '<th>ID</th><th>工作</th><th>规模</th><th>跑了什么 baseline</th><th>人类线</th><th>怎么报结果</th>') +
        '</tr></thead><tbody>' +
        RW.works.map((w) => {
          const h = HUMAN[w.human] || ['—', '—'];
          const colour = w.human === 'yes' ? 'var(--ab-p)'
            : (w.human === 'unchecked' ? 'var(--gap-absent)' : 'var(--gap-hard)');
          return `<tr><td class="term">${esc(w.id)}</td>` +
            `<td class="term"><a class="text-link" href="${esc(w.url)}" target="_blank" ` +
            `rel="noopener">${esc(w.name)}</a></td>` +
            `<td>${esc(of(w, 'scale'))}</td><td>${esc(of(w, 'baselines'))}</td>` +
            `<td class="term" style="color:${colour}">${esc(pick(h[0], h[1]))}</td>` +
            `<td>${esc(of(w, 'reporting'))}</td></tr>`;
        }).join('') + '</tbody></table>';
      // a <p> cannot contain a <p>: the browser would close the outer one and the styling would fall off
      $('lg-rw-takeaways').innerHTML = RW.takeaways.map((t2) =>
        `<div class="lg-q" style="margin:10px 0"><p>${esc(pick(t2.zh, t2.en))}</p></div>`).join('');
      $('lg-rw-req').innerHTML = RW.requirements.map((r) =>
        `<p class="lg-warn">${esc(r.from)} — ${esc(pick(r.zh, r.en))}</p>`).join('');
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
