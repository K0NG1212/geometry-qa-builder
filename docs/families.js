'use strict';
(()=>{
 const $=id=>document.getElementById(id);
 const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ABILITY={perception:'感知',inference:'推断',design:'设计'};
 const STATUS={implemented:'已接通',pilot:'新族试跑',existing_legacy:'旧题待迁移',rebuild_needed:'需重建',planned:'已规划',blocked:'暂不开放'};
 const DOMAIN={quantum:'量子',chemistry:'化学',materials:'材料',biology:'生物'};
 const pretty=x=>JSON.stringify(x,null,2);
 let cov,fam,indep,ability='all',student,teacher,numeric;

 function save(obj,name){const url=URL.createObjectURL(new Blob([pretty(obj)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}

 // ---------- coverage table ----------
 function counters(){
  const s=cov.summary,st=s.status;
  const cells=[[s.types_defined,'题型已定义'],[s.types_with_running_code,'题型有可运行代码（已接通 '+(st.implemented||0)+' + 新族 '+(st.pilot||0)+'）'],
   [s.development_instances,'新开发实例（全部待审）'],[s.independent_pass+' / '+s.independent_checked,'独立检查器通过'],[s.instance_failures,'实例构造失败（已记录）'],[s.legacy_candidates,'旧候选（保留 '+s.legacy_decisions.retain+' / 小修 '+s.legacy_decisions.revise+' / 重建 '+s.legacy_decisions.rebuild+'）']];
  $('cov-counters').innerHTML=cells.map(([n,t])=>`<div><strong>${esc(n)}</strong><span>${esc(t)}</span></div>`).join('')+
   '<div class="by-ability">'+Object.entries(s.by_ability).map(([a,c])=>`<p><b>${esc(ABILITY[a])}</b> `+Object.entries(c).map(([k,v])=>`${esc(STATUS[k]||k)} ${v}`).join(' · ')+'</p>').join('')+'</div>';
  $('cov-headline').textContent=s.types_with_running_code+' 类 · '+s.development_instances+' 例';
  $('cov-subline').textContent='有代码的题型 / 本轮新开发实例；共定义 '+s.types_defined+' 类';
 }
 function detail(r){
  const list=x=>(x&&x.length)?x.map(esc).join('，'):'—';
  const links=x=>(x&&x.length)?x.map(p=>`<a href="https://github.com/K0NG1212/geometry-qa-builder/blob/main/${esc(p)}">${esc(p)}</a>`).join('，'):'—';
  return `<dl class="facts"><dt>考点与意义</dt><dd>${esc(r.concept)}</dd><dt>输入</dt><dd>${esc(r.inputs)}</dd><dt>物理条件</dt><dd>${esc(r.physical_conditions)}</dd>
  <dt>输入尺度</dt><dd>${esc(r.input_scale)}</dd><dt>推理尺度</dt><dd>${esc(r.reasoning_scale)}；声明区间 ${list(r.scale_cells)}；实例实测 ${list(r.instance_reasoning_cells)}</dd><dt>尺度限制</dt><dd>${esc(r.scale_limits)}</dd>
  <dt>来源依据</dt><dd>${esc(r.source_basis)}</dd><dt>正确答案怎么得到</dt><dd>${esc(r.answer_method)}</dd><dt>干扰项机制</dt><dd>${list(r.distractor_mechanisms)}</dd><dt>四选一校验</dt><dd>${esc(r.four_choice_validation)}</dd>
  <dt>独立检查器</dt><dd>${esc(r.independent_checker||'—')}${r.instance_count?`（${r.independent_pass}/${r.instance_count} 通过）`:''}</dd><dt>代码</dt><dd>${links(r.code)}</dd><dt>测试</dt><dd>${links(r.tests)}</dd><dt>M0–M6</dt><dd>${esc(r.builder_modules)}</dd>
  <dt>旧题族 / 旧题</dt><dd>${list(r.legacy_families)}<br>${list(r.legacy_qa)}</dd><dt>新实例</dt><dd>${list(r.instance_ids)}${r.instance_failures?`（另有 ${r.instance_failures} 例构造失败，已记录）`:''}</dd><dt>缺口 / 下一步</dt><dd>${esc(r.gap)}</dd></dl>`;
 }
 function table(){
  const status=$('cov-status').value;
  const rows=cov.rows.filter(r=>(ability==='all'||r.ability===ability)&&(status==='all'||r.status===status)).sort((a,b)=>a.priority-b.priority);
  $('cov-rows').innerHTML=rows.map(r=>{const d=r.legacy_decisions,legacy=r.legacy_qa.length?`${r.legacy_qa.length}（${Object.entries(d).map(([k,v])=>({retain:'保',revise:'修',rebuild:'重'}[k]||k)+v).join(' ')}）`:'—';
   return `<tr class="cov-row" tabindex="0" aria-expanded="false" data-id="${esc(r.id)}"><td><b>${esc(r.name)}</b><small>${esc(r.id)}</small></td><td>${esc(ABILITY[r.ability])}</td><td><span class="pill ${esc(r.status)}">${esc(STATUS[r.status])}</span></td><td>${r.domains.map(d=>esc(DOMAIN[d]||d)).join(' ')}</td><td>${esc(r.scale_cells.join(', ')||'—')}</td><td>${esc(r.output_forms.join(' / '))}</td><td>${r.instance_count||'—'}</td><td>${legacy}</td></tr><tr class="cov-detail" hidden><td colspan="8">${detail(r)}</td></tr>`}).join('')||'<tr><td colspan="8">没有符合条件的题型。</td></tr>';
 }
 $('cov-rows').addEventListener('click',e=>{const row=e.target.closest('.cov-row');if(!row||e.target.closest('a'))return;const next=row.nextElementSibling;next.hidden=!next.hidden;row.setAttribute('aria-expanded',String(!next.hidden))});
 $('cov-rows').addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.classList.contains('cov-row')){e.preventDefault();e.target.click()}});
 document.querySelectorAll('.filters button').forEach(b=>b.addEventListener('click',()=>{ability=b.dataset.ability;document.querySelectorAll('.filters button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));table()}));
 $('cov-status').addEventListener('change',table);

 // ---------- family workbench ----------
 function familyName(id){const row=cov&&cov.rows.find(r=>r.engine_families.includes(id));return id==='extent_choice_v2'?'全局最大间距 / 等权回转半径（v0.2 选项）':row?row.name:id}
 function renderInstance(){
  const id=$('fam-instance').value;
  teacher=fam.teacher_answers.find(t=>t.id===id);student=fam.student_packets.find(s=>s.id===id);
  const n=fam.numeric_student_packets.find(x=>x.inputs_same_as===id);
  numeric=n?Object.assign({},n,{inputs:student.inputs}):null;delete (numeric||{}).inputs_same_as;
  const stage=fam.stage_records.find(s=>s.id===id);
  $('fam-meta').textContent=`${id} · ${ABILITY[teacher.ability]} · 族版本 ${teacher.family_version} · 来源 ${teacher.source}${teacher.license?' · 许可 '+teacher.license:''}${teacher.legacy_qa?' · 对应旧题 '+teacher.legacy_qa:''}`;
  $('fam-question').textContent=student.question;$('fam-scope').textContent='范围：'+student.scope;
  $('fam-inputs').innerHTML=student.inputs.map((x,i)=>`<details><summary>输入 ${i+1}：${esc(x.name)}（${esc(x.format)}，${esc(x.unit)}，${x.text.split('\n').length-1} 行）</summary><pre>${esc(x.text)}</pre></details>`).join('');
  $('fam-options').replaceChildren(...student.options.map(o=>{const b=document.createElement('button');b.type='button';b.textContent=o.label+' · '+o.value+(o.unit?' '+(o.unit==='angstrom'?'Å':o.unit==='degree'?'°':o.unit):'');b.addEventListener('click',()=>{$('fam-grade').textContent=o.label===teacher.correct_label?'回答正确（仅标签评分，不代表科学审核通过）。':'回答错误。可展开右侧审核记录查看原因。'});return b}));
  $('fam-grade').textContent='';$('fam-download-numeric').hidden=!numeric;
  $('fam-student').textContent=pretty(student);
  const right=teacher.option_audit.find(o=>o.is_correct);
  $('fam-answer').innerHTML=`正确答案：<b>${esc(teacher.correct_label)}</b> · ${esc(right.value)}${teacher.numeric_answer?` · 数值作答：${esc(teacher.numeric_answer.value)} ${esc(teacher.numeric_answer.unit)}（容差 ${esc(teacher.numeric_answer.tolerance)}）`:''}`;
  $('fam-audit').innerHTML=teacher.option_audit.map(o=>`<tr class="${o.is_correct?'right':''}"><td>${esc(o.label)}</td><td>${esc(o.value)}${o.property!==undefined?`<small>${esc(o.property)} ${esc(o.unit)}</small>`:''}${o.relative_amplitude!==undefined?`<small>|F|/F000 = ${esc(o.relative_amplitude)}</small>`:''}</td><td>${esc(o.rule||o.source_id)}</td><td>${esc(o.reason)}</td></tr>`).join('');
  $('fam-checks').textContent=pretty({checks:teacher.checks,scales:teacher.scales,rank:teacher.rank,rank_shortcuts:teacher.rank_shortcuts,target_position:teacher.target_position,option_order:teacher.option_order,input_hashes:teacher.input_hashes});
  $('fam-excluded').textContent=pretty(teacher.excluded_candidates);
  $('fam-stages').textContent=pretty(stage);
  const ic=indep.results.find(x=>x.id===id);
  $('fam-independent').textContent=ic?(ic.status==='pass'?'独立检查器：通过（'+ic.method+'）':'独立检查器：未通过 — '+ic.problem):'独立检查器：无记录';
  $('fam-independent').className='independent '+(ic&&ic.status==='pass'?'ok':'bad');
  $('fam-independent-json').textContent=pretty(ic||{});
  const module=fam.report&&fam.stage_records.find(s=>s.id===id).define.module;$('fam-code').textContent=fam.code[module]||'';
 }
 function renderFamily(){
  const f=$('fam-select').value,items=fam.teacher_answers.filter(t=>t.family===f);
  $('fam-instance').innerHTML=items.map(t=>`<option value="${esc(t.id)}">${esc(t.id)}${t.legacy_qa?' · 源自 '+esc(t.legacy_qa):''}</option>`).join('');
  const r=fam.report.by_family[f],fails=fam.report.failures.filter(x=>x.family===f);
  $('fam-report').textContent=pretty({family:f,by_family:r,failures:fails,batch_positions:fam.report.correct_position_counts,difficulty_note:fam.report.difficulty_note,model_calls:fam.report.model_calls,catalog_admitted:fam.report.catalog_admitted});
  renderInstance();
 }
 $('fam-select').addEventListener('change',renderFamily);$('fam-instance').addEventListener('change',renderInstance);
 $('fam-download').addEventListener('click',()=>student&&save(student,student.id+'-student.json'));
 $('fam-download-numeric').addEventListener('click',()=>numeric&&save(numeric,numeric.id+'-student.json'));

 Promise.all(['data/task-coverage.json','data/family-workbench.json','data/independent-check.json'].map(u=>fetch(u).then(r=>{if(!r.ok)throw Error(u+' '+r.status);return r.json()}))).then(([c,f,i])=>{
  cov=c;fam=f;indep=i;counters();
  $('fam-independent-summary').textContent=`本批 ${i.checked} 例，独立检查通过 ${i.passed} 例，失败 ${i.failed.length} 例；模型调用 ${i.model_calls}。检查器版本 ${i.checker_version}。`;
  $('fam-checker-code').textContent=Object.entries(i.checker_code||{}).map(([k,v])=>'# ==== '+k+'\n'+v).join('\n');
  $('cov-status').innerHTML='<option value="all">全部状态</option>'+Object.keys(cov.axes.status).map(k=>`<option value="${esc(k)}">${esc(STATUS[k]||k)}</option>`).join('');
  table();
  const order=['named_bond_angle','backbone_torsion','force_path_derivative','kinematic_extinction','conformer_target_selection','extent_choice_v2'];
  const present=order.filter(x=>fam.teacher_answers.some(t=>t.family===x));
  $('fam-select').innerHTML=present.map(x=>{const t=fam.teacher_answers.find(y=>y.family===x);return `<option value="${esc(x)}">${esc(ABILITY[t.ability])} · ${esc(familyName(x))}</option>`}).join('');
  const r=fam.report;$('fam-summary').textContent=`运行 ${fam.run}：尝试 ${r.attempted} 例，程序核验通过 ${r.passed} 例，构造失败 ${r.failures.length} 例（已记录原因）；模型调用 0；全部待人工审核，新增题库 0。`;
  renderFamily();
 }).catch(e=>{$('fam-summary').textContent='记录加载失败：'+e.message;$('load-error').hidden=false});
})();
