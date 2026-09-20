'use strict';
const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names={quantum:'量子 / 电子结构',chemistry:'化学',biology:'生物',materials:'材料'};
fetch('data/admission-audit.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(a=>{
 document.querySelector('#audit-stats').innerHTML=[[a.target,'原型目标'],[a.screened,'初筛候选'],[a.remaining_screened,'还缺初筛候选'],[a.human_review_count,'待独立人工审核'],[a.formal_ready,'正式审核通过'],[a.remaining_formal,'距正式完成的缺口']].map(([n,t])=>`<article><strong>${n}</strong>${t}</article>`).join('');
 document.querySelector('#audit-scope').textContent=a.scope+' 当前保留 '+a.lifecycle_counts.active+' 条原型、'+a.lifecycle_counts.rework+' 条待重构、'+a.lifecycle_counts.backlog+' 条待材料草案、'+a.lifecycle_counts.archived+' 条历史归档。初筛候选仍可能在人工审核中被退回。';
 const link=id=>`<a class="text-link" href="index.html?qa=${encodeURIComponent(id)}#questions">${escapeHTML(id)} · 完整记录 ↗</a>`;
 document.querySelector('#audit-queue').innerHTML=a.human_review_ids.map(link).join('');
 document.querySelector('#audit-cells').innerHTML=a.cells.map(c=>`<tr><td>${names[c.domain]}</td><td>${c.range_nm.join('–')} nm</td><td>${c.screened_count} / ${c.target}</td><td>${c.abilities.perception} / ${c.abilities.inference} / ${c.abilities.design}</td><td>${c.remaining}</td></tr>`).join('');
 document.querySelector('#audit-records').innerHTML=a.records.map(r=>`<details class="audit-record"><summary>${escapeHTML(r.id)} · ${escapeHTML(r.title)} · ${r.human_review_queue?'可进入人工审核':'需先补全／重构或已归档'}</summary><p>${escapeHTML(r.reason)}</p><p>${Object.entries(r.checks).map(([k,v])=>`${v?'✓':'—'} ${escapeHTML(k)}`).join('；')}</p><p>下一步：${escapeHTML(r.next)}</p>${link(r.id)}</details>`).join('');
 document.querySelector('#audit-directions').innerHTML=a.directions.map(t=>`<details class="audit-record"><summary>${escapeHTML(t.id)} · ${escapeHTML(t.state)} · 关联 ${t.instance_ids.length} 条实例记录</summary><p>${t.instance_ids.map(link).join(' · ')||'尚无完整实例入口，不能计入题量。'}</p><p>${escapeHTML(t.next)}</p></details>`).join('');
}).catch(e=>{document.querySelector('#audit-error').hidden=false;console.error(e)});
