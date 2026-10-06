'use strict';
(function(){
 const $=id=>document.getElementById(id);
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const ABILITY={perception:'感知',inference:'推断',design:'设计'};
 const DOMAIN={chemistry:'化学',biology:'生物',materials:'材料',quantum:'量子'};
 const cellName=c=>{const [d,b]=c.split(' ');return (DOMAIN[d]||d)+' '+b.replace('-','–')};
 let data,step=0,filter='all',chosen=null;

 function stepView(){
  const s=data.steps[step],stage=data.stages.find(x=>x.id===s.stage);
  $('module-list').innerHTML=data.steps.map((x,i)=>`<button class="module-button" data-step="${i}" aria-current="${i===step}"><span>${String(i+1).padStart(2,'0')}</span><div><b>${esc(x.title)}</b><small>${esc((data.stages.find(y=>y.id===x.stage)||{}).title)} · ${esc(x.m)}</small></div></button>`).join('');
  const files=s.files.map(f=>f.missing?`<p class="file-list">${esc(f.path)}（未找到）</p>`:
   `<details><summary>${esc(f.path)}<span>${f.lines} 行 · sha256 ${esc(f.sha256.slice(0,12))}…</span></summary><div class="source-top"><span>${f.source?'当前版本源代码':'文件较大或非代码，见 GitHub'}</span><a href="${esc(f.url)}" target="_blank" rel="noopener">在 GitHub 查看 ↗</a></div>${f.source?`<pre>${esc(f.source)}</pre>`:''}</details>`).join('');
  $('module-detail').innerHTML=`<div class="detail-top"><div><span class="tag">${esc(stage?stage.title:'')} · ${esc(s.m)}</span><h2>${String(step+1).padStart(2,'0')} ${esc(s.title)}</h2></div></div><p class="purpose">${esc(s.purpose)}</p>
   ${s.input||s.output?`<div class="io"><div><span>INPUT</span><p>${esc(s.input||'—')}</p></div><div><span>OUTPUT</span><p>${esc(s.output||'—')}</p></div></div>`:''}
   <div class="explanation"><h3>保证</h3><ul class="guarantee">${s.guarantees.map(g=>`<li>${esc(g)}</li>`).join('')}</ul></div>
   ${s.limits?`<div class="limit"><h3>局限</h3><p>${esc(s.limits)}</p></div>`:''}
   ${s.command?`<div class="improve"><h3>命令</h3><code class="command">${esc(s.command)}</code></div>`:''}
   ${files?`<div class="files-heading"><h3>相关代码与文件</h3></div>${files}`:''}`;
  document.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',()=>{step=+b.dataset.step;stepView()}));
 }

 function famView(){
  const routes=data.routes,list=data.families.filter(f=>filter==='all'||f.route===filter||f.ability===filter||(filter==='enum'&&f.enumerator));
  const opts=[['all','全部'],['perception','感知'],['inference','推断'],['design','设计']].concat(Object.entries(routes).map(([k,v])=>[k,v.label])).concat([['enum','已有枚举器']]);
  $('fam-filters').innerHTML=opts.map(([k,l])=>`<button data-filter="${k}" aria-pressed="${k===filter}">${esc(l)}</button>`).join('');
  $('fam-rows').innerHTML=list.map(f=>`<tr data-fam="${esc(f.id)}" class="${f.id===chosen?'sel':''}"><td><b>${esc(f.registry.name||f.id)}</b><br><span class="mono" style="font:11px monospace;color:var(--muted)">${esc(f.id)}</span></td><td>${esc(ABILITY[f.ability])}</td><td><span class="pill ${esc(f.route)}">${esc(routes[f.route].label)}</span>${f.enumerator?'<span class="pill">枚举器</span>':''}</td><td>${f.instances}</td><td>${f.cells.map(c=>`<span class="pill">${esc(cellName(c))}</span>`).join('')}</td><td style="font-size:12px">${esc(f.checker_method||'—')}</td></tr>`).join('');
  document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;famView()}));
  document.querySelectorAll('[data-fam]').forEach(r=>r.addEventListener('click',()=>{chosen=r.dataset.fam;famView();$('fam-detail').scrollIntoView({block:'nearest'})}));
  const f=data.families.find(x=>x.id===chosen);
  if(!f){$('fam-detail').innerHTML='<p class="footnote">点击任一行查看该题型族的考点、物理条件、错误机制、局限与代码。</p>';return}
  const r=f.registry;
  $('fam-detail').innerHTML=`<div class="limit" style="background:#fff;border-left-color:var(--green)"><h3>${esc(r.name||f.id)} <span class="tag">${esc(ABILITY[f.ability])} · v${esc(f.version)}</span></h3>
   <dl class="kv">${r.concept?`<dt>考点</dt><dd>${esc(r.concept)}</dd>`:''}${r.physical_conditions?`<dt>物理条件</dt><dd>${esc(r.physical_conditions)}</dd>`:''}${r.answer_method?`<dt>答案方法</dt><dd>${esc(r.answer_method)}</dd>`:''}
   ${r.distractor_mechanisms?`<dt>错误机制</dt><dd>${r.distractor_mechanisms.map(m=>`<span class="pill">${esc(m)}</span>`).join('')}</dd>`:''}${r.validation?`<dt>验证</dt><dd>${esc(r.validation)}</dd>`:''}${r.limits?`<dt>局限</dt><dd>${esc(r.limits)}</dd>`:''}
   <dt>数据路线</dt><dd>${esc(data.routes[f.route].label)}：${esc(data.routes[f.route].text)}</dd>
   <dt>出题代码</dt><dd><a class="text-link" href="${esc(f.module_url)}" target="_blank" rel="noopener">${esc(f.module)} ↗</a></dd>
   <dt>独立检查器</dt><dd>${f.checker?`<a href="${esc(f.checker_url)}" target="_blank" rel="noopener">${esc(f.checker)} ↗</a>（${esc(f.checker_method||'')}）`:'—'}</dd>
   <dt>实例</dt><dd>${f.instances} 条规格，${f.active} 道在当前题库${f.example?` · <a href="templates.html?instance=${encodeURIComponent(f.example)}#workbench">在工作台查看样例 ${esc(f.example)} ↗</a>`:''}</dd></dl></div>`;
 }

 function capView(){
  const c=data.capacity,t=c.totals;
  $('cap-note').textContent=`枚举器从 ${c.structures.length} 个已提交的结构（${c.structures.join('、')}）中列出所有可出的候选，按固定种子每个结构抽 ${c.sample_per_structure} 个，交给题型族生成（不合格的由题型族拒绝），再用独立检查器复核。共 ${t.proposals} 个候选，抽样 ${t.sampled} 个，题型接受 ${t.accepted} 个，独立检查 ${t.checker_pass} / ${t.checker_checked} 通过；答案位置 A ${t.positions.A} / B ${t.positions.B} / C ${t.positions.C} / D ${t.positions.D}（${t.position_balance_ok?'各族均在容差内':'有族超出容差'}）。按接受率估计，仅这 ${c.structures.length} 个结构就可出约 ${t.estimated_admissible} 道。这只是容量探针，不入库：批量生产要等题型通过 L1/L2 人工审定。`;
  const fam=Object.fromEntries(data.families.map(f=>[f.id,f]));
  $('cap-rows').innerHTML=c.rows.map(r=>`<tr><td>${esc((fam[r.family]||{}).registry?.name||r.family)}</td><td>${esc(r.structure)}</td><td>${r.proposals}</td><td>${r.sampled}</td><td>${r.accepted}</td><td>${r.checker_pass}</td><td>${r.estimated_admissible}</td></tr>`).join('');
 }

 function batchView(p){
  const s=p.summary,t=p.rule.tiers,DN={quantum:'量子',chemistry:'化学',materials:'材料',biology:'生物'};
  $('bp-note').textContent=`${p.status_note}三档目标、多样性下限与上限写在 templates/batch-selection-rule.json；差距由 tools/batch_plan.py 计算：已入库的题加上枚举器估计容量（${p.enumeration_run}），按“题型族 × 来源”配对，在全部上限下用最大流求最多可选的题数。上限同时生效、最后相加，不是相乘。`;
  $('bp-stats').innerHTML=[[s.target,'目标题量（16 格合计）'],[s.max_selectable,'现有数据在上限下最多可选'],[s.max_balanced,'同时满足三类能力比例'],[s.cells_meeting_rule+' / 16','完全满足规则的格子']].map(([n,l])=>`<div><strong>${esc(n)}</strong><span>${esc(l)}</span></div>`).join('');
  const cells=Object.fromEntries(p.cells.map(c=>[c.cell,c])),bins=['0.1-1','1-10','10-100','100-1000'];
  let html='<span></span>'+bins.map(b=>`<span class="h">${esc(b.replace('-','–'))} nm</span>`).join('');
  for(const d of ['quantum','chemistry','materials','biology']){
   html+=`<span class="h" style="align-self:center">${DN[d]}</span>`;
   for(const b of bins){const c=cells[d+' '+b];
    html+=`<button class="bp-cell" data-bp="${esc(c.cell)}" aria-pressed="false"><b>${c.max_selectable}</b> / ${c.target}<span class="bp-tier ${c.tier}">${c.tier}</span>
     <div class="bp-bar"><i style="width:${Math.round(100*c.max_selectable/c.target)}%"></i></div><div class="bp-bar"><i class="bal" style="width:${Math.round(100*c.max_balanced/c.target)}%"></i></div>
     <span style="color:var(--muted)">族 ${c.families} · 来源 ${c.sources} · 缺口 ${c.gaps.length}</span></button>`}
  }
  $('bp-grid').innerHTML=html;
  const show=name=>{const c=cells[name];document.querySelectorAll('[data-bp]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.bp===name)));
   const fam=Object.entries(c.family_flow).map(([f,n])=>`${esc(f)} ${n}`).join('、');
   $('bp-detail').innerHTML=`<div class="limit" style="background:#fff;border-left-color:var(--green)"><h3>${esc(DN[c.cell.split(' ')[0]])} ${esc(c.cell.split(' ')[1].replace('-','–'))} nm <span class="tag">${esc(c.tier)} 档 · ${esc(t[c.tier].label)} · 目标 ${c.target}</span></h3>
    <dl class="kv"><dt>最多可选</dt><dd>${c.max_selectable}（满足能力比例 ${c.max_balanced}）</dd>
    <dt>题型族</dt><dd>${c.families} 个（感知 ${c.families_by_ability.perception}、推断 ${c.families_by_ability.inference}、设计 ${c.families_by_ability.design}）</dd>
    <dt>各能力最多</dt><dd>感知 ${c.ability_max.perception}、推断 ${c.ability_max.inference}、设计 ${c.ability_max.design}</dd>
    <dt>来源</dt><dd>${c.sources} 个${c.paper_systems.length?'；论文参数体系 '+c.paper_systems.length+' 个':''}</dd>
    <dt>候选池</dt><dd>已入库 ${c.pool.admitted} 道 + 枚举估计 ${c.pool.enumerated} 道</dd>
    <dt>最大选择中各族</dt><dd style="font-size:12.5px">${fam||'—'}</dd>
    <dt>缺口</dt><dd>${c.gaps.length?'<ul style="margin:0;padding-left:18px">'+c.gaps.map(g=>`<li>${esc(g)}</li>`).join('')+'</ul>':'满足规则'}</dd></dl></div>`};
  document.querySelectorAll('[data-bp]').forEach(x=>x.addEventListener('click',()=>show(x.dataset.bp)));
  show('biology 1-10');
  const row=(label,f)=>`<tr><th>${esc(label)}</th>${['A','B','C'].map(k=>`<td>${esc(f(t[k]))}</td>`).join('')}</tr>`;
  $('bp-tiers').innerHTML=`<thead><tr><th></th>${['A','B','C'].map(k=>`<th>${k} 档：${esc(t[k].label)}</th>`).join('')}</tr></thead><tbody>`+
   row('每格目标',x=>x.target+' 道')+row('题型族',x=>`≥ ${x.min_families}，每类能力 ≥ ${x.min_families_per_ability}`+(x.min_systems?`；≥ ${x.min_systems} 个论文参数体系`:''))+
   row('来源（结构或论文）',x=>'≥ '+x.min_sources)+row('一个题型族最多',x=>x.max_per_family+' 道')+row('一个来源最多',x=>x.max_per_source+' 道')+
   row('同一来源 × 同一族最多',x=>x.max_per_family_source+' 道')+'</tbody>';
  const g=p.rule.global;
  $('bp-global').innerHTML=[`三类能力各约 1/3（±${Math.round(p.rule.ability_share.tolerance*100)}%）`,`论文参数模型题 ≤ ${Math.round(g.max_paper_parameter_share*100)}%（现可选题中占 ${(s.paper_parameter_share_of_selectable*100).toFixed(1)}%）`,
   `实验证据型题 ≤ ${Math.round(g.max_experimental_evidence_share*100)}%`,`全库：一个来源 ≤ ${g.max_per_source} 道，一个题型族 ≤ ${g.max_per_family} 道`,'答案位置：'+g.answer_positions,'近重复：'+g.near_duplicates]
   .map(x=>`<li>${esc(x)}</li>`).join('');
  $('bp-pending').innerHTML=p.rule.pending_advisor.map(x=>`<li>${esc(x)}</li>`).join('');
 }
 const batchLoaded=fetch('data/batch-plan.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(batchView).catch(e=>{$('bp-note').textContent='未能加载 data/batch-plan.json';console.error(e)});
 const systemLoaded=fetch('data/system.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{
  data=d;const s=d.summary;
  $('sys-families').textContent=s.families;
  $('sys-families-note').textContent=`题型族 · ${s.checkers} 个独立检查器`;
  $('sys-summary').innerHTML=`${s.family_modules} 个出题模块，约 ${s.generator_lines} 行出题代码、${s.checker_lines} 行检查代码。<br>最新运行 ${esc(s.run)}：生成 ${s.passed} / ${s.attempted}，独立复核 ${s.independent_passed} / ${s.independent_checked}。<br>${s.tests} 项自动测试。`;
  $('sys-boundary').textContent=`模型调用 ${s.model_calls} 次 · 人工审核（L1–L3）尚未开始`;
  $('sys-run').textContent=`数据来自 ${s.run} · 由 tools/export_system.py 从仓库生成`;
  $('sys-principles').innerHTML=d.principles.map(p=>`<div><b>${esc(p.title)}</b><p>${esc(p.text)}</p></div>`).join('');
  $('sys-stages').innerHTML=d.stages.map(x=>`<div><b>${esc(x.title)}</b><span>${esc(x.m)}</span><p>${esc(x.text)}</p></div>`).join('');
  $('fam-note').textContent=`共 ${s.families} 个题型族：感知 ${s.abilities.perception}、推断 ${s.abilities.inference}、设计 ${s.abilities.design}。按数据路线：`+Object.entries(d.routes).map(([k,v])=>`${v.label} ${s.routes[k]}`).join('、')+`。已有枚举器的族：${s.enumerated_families.length} 个。`;
  $('sys-facts').innerHTML=[
   ['检查器不导入出题代码','tests/test_checkers.py 用语法树扫描 checkers/ 的全部 import，出现 task_families、family_engine 等即失败。'],
   ['参数从题干读取','检查器用正则从题干文字取出原子、条件和参数再计算；测试会篡改题干中的数字或条件，要求检查器判为不通过。'],
   ['答案键不泄漏','学生包中出现 correct_label、option_audit 等任何答案字段，检查即失败。'],
   ['来源可追溯','每道题的答案键记录附件 SHA-256；检查器重新读取已发布的资产核对哈希。'],
   ['运行可重放','每次运行快照出题代码、规格和注册表的哈希；导出前完整重放，代码不一致就拒绝发布。'],
   ['审核绑定代码','L1/L2 审核记录绑定代码与注册表行的 SHA-256；代码一改，记录自动失效，必须重审。']
  ].map(([b,p])=>`<div><b>${esc(b)}</b><p>${esc(p)}</p></div>`).join('');
  $('sys-repro').innerHTML=d.reproduce.map(x=>`<li>${esc(x.title)}<code class="command">${esc(x.command)}</code></li>`).join('');
  stepView();famView();capView();
 }).catch(e=>{$('sys-error').hidden=false;console.error(e)});
 Promise.all([batchLoaded, systemLoaded]).then(()=>{   // sections render after load: re-apply #anchor links
  if(location.hash){const el=document.getElementById(location.hash.slice(1));if(el)el.scrollIntoView()}
 });
})();
