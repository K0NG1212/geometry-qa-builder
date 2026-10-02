'use strict';
(function(){
 const $=id=>document.getElementById(id);
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ABILITY={perception:'感知',inference:'推断',design:'设计'};
 const STATE={pending:'待审',approved:'通过',revise:'需修改',stale:'已失效（代码或模板已变）'};
 const pill=s=>`<span class="pill ${esc(s)}">${esc(STATE[s]||s)}</span>`;
 let data,kind='all';
 function sample(s){
  if(s.instance) return `<div class="rv-card"><b>${esc(s.instance)}</b> · 正确 ${esc(s.correct_label)}<pre>${esc(s.question)}\n\n${s.options.map(o=>esc(o.label+'. '+o.value+(o.unit?' '+o.unit:''))).join('\n')}\n\n附件：${esc(s.inputs.join('、'))}</pre><p>${s.audit.map(a=>`${esc(a.label)} · ${esc(a.rule)}：${esc(a.reason)}`).join('<br>')}</p><a class="text-link" href="templates.html?instance=${encodeURIComponent(s.instance)}#workbench">在工作台打开 ↗</a></div>`;
  return `<div class="rv-card"><b>${esc(s.record)}</b><pre>${esc(s.question)}</pre><p>答案：${esc(s.answer)}</p><p>${esc(s.validation)}</p><a class="text-link" href="index.html?qa=${encodeURIComponent(s.record)}#questions">完整记录 ↗</a></div>`;
 }
 function detail(u){
  const t=u.card.template;
  const rows=Object.entries(t).map(([k,v])=>`<tr><th>${esc(k)}</th><td>${esc(Array.isArray(v)?v.join('、'):v)}</td></tr>`).join('');
  const b=(o)=>Object.entries(o).map(([k,v])=>`${esc(k)}: <span class="mono">${esc((v||'—').slice(0,16))}…</span>`).join('<br>');
  return `<table class="rv-table">${rows}</table><p><b>L1 绑定</b><br>${b(u.bindings.L1)}</p><p><b>L2 绑定</b><br>${b(u.bindings.L2)}</p><h4>样例</h4>${u.card.samples.map(sample).join('')}
   <p class="mono">记录命令：python tools/review.py record-l1 --unit ${esc(u.unit)} --reviewer "姓名" --decision approved|revise --notes "…"</p>`;
 }
 function units(){
  const list=data.units.filter(u=>kind==='all'||u.kind===kind);
  $('rv-units').innerHTML=list.map((u,i)=>`<tr id="u-${esc(u.unit)}"><td><details><summary><b>${esc(u.unit)}</b>${u.registry_id?` <small>${esc(u.registry_id)}</small>`:''}</summary>${detail(u)}</details></td><td>${esc(ABILITY[u.ability]||u.ability)}</td><td>${u.instances}</td><td>${pill(u.L1)}</td><td>${pill(u.L2)}</td><td class="mono">${esc(u.checker?u.checker+':'+u.checker_function:'（旧模板：审阅计算代码）')}</td></tr>`).join('');
 }
 function jump(open){
  const want=new URLSearchParams(location.search).get('unit'),row=want&&document.getElementById('u-'+want);
  if(row){if(open)row.querySelector('details').open=true;row.scrollIntoView({block:'start'})}
 }
 fetch('data/review-queue.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{
  data=d;const s=d.summary;
  $('rv-note').textContent=`${d.date} · ${d.note} 模型调用 ${s.model_calls} 次。`;
  $('rv-stats').innerHTML=[[s.units,`审核单元（${s.families} 题型族 + ${s.legacy_units} 旧模板；范围：${s.scope==='selection'?'160 道挑选，全部 active 需 '+s.units_all_active+' 个':'全部 active'}）`],[s.L1.approved+' / '+s.units,'L1 已通过'],[s.L2.approved+' / '+s.units,'L2 已通过'],[s.stages.formal+' / '+s.instances,'实例正式计入'],
   [s.stages.L0,'停在 L0（已自动核验）'],[s.l3_sample,`下一批 L3 抽样（${s.l3_strata} 层）`],[s.l3_steady_state_sample,'稳定后同规模抽样'],[s.reviews_recorded.L1+s.reviews_recorded.L2+s.reviews_recorded.L3,'已记录审核']].map(([n,t])=>`<article><strong>${esc(n)}</strong>${esc(t)}</article>`).join('');
  $('rv-questions').innerHTML=d.questions.questions.map(q=>`<li><b>${esc(q.label)}</b>（${esc(q.id)}）：${esc(q.prompt)}</li>`).join('');
  $('rv-qsha').textContent='四问文件 SHA-256：'+d.questions_sha256+'（改动四问会使已有 L3 结果失效）';
  $('rv-l3-title').textContent=`下一批 L3 抽样计划（${s.next_l3_batch}）`;
  $('rv-l3-note').textContent=`共 ${s.l3_strata} 层、${s.l3_sample} 道。首批中所有题型与来源都是新的，按规则全检；原型阶段多数层只有 1–3 道，所以稳定后抽样也有 ${s.l3_steady_state_sample} 道，批量生产后比例才明显下降。生成提示词：python tools/review.py l3-prompts --batch ${s.next_l3_batch}`;
  $('rv-l3').innerHTML=d.l3_plan.map(p=>`<tr><td>${esc(p.stratum)}</td><td>${p.size}</td><td>${p.sample}</td><td>${esc(p.rule)}</td><td class="mono">${esc(p.ids.join(' '))}</td></tr>`).join('');
  units();
  jump(true);
  document.querySelectorAll('.rv-filter button').forEach(b=>b.addEventListener('click',()=>{kind=b.dataset.kind;document.querySelectorAll('.rv-filter button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));units()}));
 }).catch(e=>{$('rv-error').hidden=false;console.error(e)});
 fetch('data/prototype-selection.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{
  const s=d.summary,mark=x=>(x.pending?'*':'')+(x.form==='legacy'?'†':x.form==='family-version'?'‡':'');
  const pend=Object.entries(s.pending_decision).map(([k,n])=>`${d.pending_labels[k]}：${n} 道`).join('；');
  $('sel-note').textContent=`规则 v${d.rule_version}（${d.status_note}）选中 ${s.selected} 道、备用 ${s.reserve} 道；感知 ${s.abilities.perception}、推断 ${s.abilities.inference}、设计 ${s.abilities.design}。审核单元 ${s.review_units} 个（${s.family_units} 题型族 + ${s.legacy_units} 旧模板）。选中题里属于待教授决定类别的：${pend}。`;
  $('sel-steps').innerHTML=d.steps.map(x=>`<li>${esc(x)}</li>`).join('');
  $('sel-cells').innerHTML=d.cells.map(c=>`<tr><td>${esc(c.cell)}</td><td>${c.abilities.perception} / ${c.abilities.inference} / ${c.abilities.design}</td><td class="mono">${c.selected.map(x=>`<a href="index.html?qa=${encodeURIComponent(x.id)}#questions">${esc(x.id)}</a>${esc(mark(x))}`).join(' ')}</td><td class="mono">${c.reserve.map(x=>esc(x.id)).join(' ')||'—'}</td><td>${esc(c.rationale)}</td></tr>`).join('');
  jump(false);
 }).catch(e=>{$('sel-note').textContent='未能加载 data/prototype-selection.json';console.error(e)});
})();
