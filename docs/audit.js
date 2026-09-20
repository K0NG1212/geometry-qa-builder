'use strict';
const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names={quantum:'量子 / 电子结构',chemistry:'化学',biology:'生物',materials:'材料'};
fetch('data/admission-audit.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(a=>{
 document.querySelector('#audit-stats').innerHTML=[[a.target,'原型目标'],[a.screened,'初筛候选'],[a.remaining_screened,'还缺初筛候选'],[a.human_review_count,'待独立人工审核'],[a.formal_ready,'正式审核通过'],[a.remaining_formal,'距正式完成的缺口']].map(([n,t])=>`<article><strong>${n}</strong>${t}</article>`).join('');
 document.querySelector('#audit-scope').textContent='统计仅包含当前完整候选。初筛不等于人工审核通过；旧草案和测试题已移至历史存档。';
 const link=id=>`<a class="text-link" href="index.html?qa=${encodeURIComponent(id)}#questions">${escapeHTML(id)} · 完整记录 ↗</a>`;
 document.querySelector('#audit-queue').innerHTML=a.human_review_ids.map(link).join('');
 document.querySelector('#audit-cells').innerHTML=a.cells.map(c=>`<tr><td>${names[c.domain]}</td><td>${c.range_nm.join('–')} nm</td><td>${c.screened_count} / ${c.target}</td><td>${c.abilities.perception} / ${c.abilities.inference} / ${c.abilities.design}</td><td>${c.remaining}</td></tr>`).join('');
 document.querySelector('#audit-records').innerHTML=a.records.filter(r=>r.human_review_queue).map(r=>`<details class="audit-record"><summary>${escapeHTML(r.id)} · ${escapeHTML(r.title)} · ${r.human_review_queue?'可进入人工审核':'需先补全／重构或已归档'}</summary><p>${escapeHTML(r.reason)}</p><p>${Object.entries(r.checks).map(([k,v])=>`${v?'✓':'—'} ${escapeHTML(k)}`).join('；')}</p><p>下一步：${escapeHTML(r.next)}</p>${link(r.id)}</details>`).join('');

}).catch(e=>{document.querySelector('#audit-error').hidden=false;console.error(e)});
