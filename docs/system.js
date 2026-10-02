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

 fetch('data/system.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{
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
})();
