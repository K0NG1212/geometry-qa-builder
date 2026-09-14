'use strict';
(() => {
  const list=document.getElementById('module-list'),detail=document.getElementById('module-detail');
  const repo='https://github.com/K0NG1212/geometry-qa-builder/blob/main/';
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels={'module.py':'实现代码','prompt.md':'AI 提示词','schema.json':'输入 / 输出契约','README.md':'维护说明','settings.json':'当前范围配置','retrieval.md':'检索操作规程'};
  let modules=[];
  function render(){
    const focused=document.activeElement?.dataset?.module;
    const id=location.hash.slice(1).toUpperCase();
    const m=modules.find(x=>x.id===id)||modules[0];
    list.innerHTML=modules.map(x=>`<button class="module-button" data-module="${esc(x.id)}" aria-current="${x.id===m.id}"><span>${esc(x.id)}</span><div><b>${esc(x.name)}</b><small>${esc(x.status)}</small></div></button>`).join('');
    detail.innerHTML=`<div class="eyebrow">${esc(m.id)} / ${esc(m.executor)}</div><div class="detail-top"><h2>${esc(m.name)}</h2><span class="tag">${esc(m.status)}</span></div><p class="purpose">${esc(m.purpose)}</p><div class="io"><div><span>INPUT / 输入</span><p>${esc(m.inputs)}</p></div><div><span>OUTPUT / 输出</span><p>${esc(m.outputs)}</p></div></div><div class="io-inspect"><h3>查看这一模块的数据</h3><p><a href="trace.html?qa=CNM001#${esc(m.id)}">查看 CNM001 本轮实际输入输出 ↗</a> · 可在记录页切换其他五道题</p><p class="footnote">${esc(m.io_example.note)}</p><div class="example-grid"><details><summary>输入示例</summary><pre><code>${esc(JSON.stringify(m.io_example.input,null,2))}</code></pre></details><details><summary>输出示例</summary><pre><code>${esc(JSON.stringify(m.io_example.output,null,2))}</code></pre></details></div><p class="file-list">实际记录：${m.inspect_files.map(esc).join(' · ')}</p></div><div class="explanation"><h3>它如何工作</h3><p>${esc(m.principle)}</p><h3>程序检查什么</h3><p>${esc(m.checks)}</p></div><div class="limit"><h3>还没有完成什么</h3><p>${esc(m.limits)}</p></div><div class="improve"><h3>下次只优化这个模块</h3><p>${esc(m.optimize)}</p><code class="command">${esc(m.test_command)}</code></div><div class="files-heading"><h3>打开实际实现文件</h3><a href="${repo}builder_modules/${encodeURIComponent(m.folder)}/README.md" target="_blank" rel="noopener">GitHub 中查看 ↗</a></div>${m.files.filter(f=>f.name!=='README.md').map(f=>`<details><summary>${labels[f.name]||esc(f.name)}<span>${esc(f.name)}</span></summary><div class="source-top"><span>${esc(f.path)}</span><a href="${repo}${f.path.split('/').map(encodeURIComponent).join('/')}" target="_blank" rel="noopener">查看源文件 ↗</a></div><pre><code>${esc(f.content)}</code></pre></details>`).join('')}<p class="footnote">页面从模块目录自动导出 · v${esc(m.version)}<br>修改字段契约后，还需要验证下游模块和完整流程。</p>`;
    detail.setAttribute('aria-busy','false');
    if(focused)list.querySelector(`[data-module="${focused}"]`)?.focus({preventScroll:true});
  }
  list.addEventListener('click',e=>{const b=e.target.closest('[data-module]');if(b)location.hash=b.dataset.module;});
  window.addEventListener('hashchange',()=>{if(modules.length)render();});
  const get=url=>fetch(url).then(r=>{if(!r.ok)throw Error(r.status);return r.json();});
  Promise.all([get('data/builder-modules.json'),get('data/builder-flow.json')]).then(([data,flow])=>{
    modules=data.modules;render();
    const choices=document.getElementById('route-choices');
    function route(id){const active=flow.routes.find(x=>x.id===id);choices.innerHTML=flow.routes.map(x=>`<button data-route-choice="${esc(x.id)}" aria-pressed="${x.id===id}">${esc(x.name)}</button>`).join('');document.getElementById('route-detail').innerHTML=`<p class="flow-path">${esc(active.flow)}</p><p>${esc(active.description)}</p>`;}
    choices.addEventListener('click',e=>{const button=e.target.closest('[data-route-choice]');if(button){route(button.dataset.routeChoice);choices.querySelector(`[data-route-choice="${button.dataset.routeChoice}"]`).focus({preventScroll:true});}});
    document.getElementById('goal-example').textContent=JSON.stringify(flow.example_goal,null,2);route('new');
  }).catch(()=>{list.textContent='模块读取失败';detail.setAttribute('aria-busy','false');document.getElementById('module-error').hidden=false;});
})();
