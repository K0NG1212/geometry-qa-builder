/* Task framework is separate from instantiated QA and candidate counts. */
(() => {
  let framework;
  let reviewData;
  let readiness;
  let catalog;
  let decision = '';
  let mode = 'reasoning';
  let ability = '';
  let lifecycle='active';
  const bins = ['0.1–1 nm','1–10 nm','10–100 nm','100–1000 nm'];
  const powers = ['10⁻¹⁰–10⁻⁹ m','10⁻⁹–10⁻⁸ m','10⁻⁸–10⁻⁷ m','10⁻⁷–10⁻⁶ m'];
  function inBin(value,i){return Number.isFinite(value)&&value>=10**(i-1)&&(value<10**i||(i===3&&value===1000));}
  const render = () => {
    if (!framework||!catalog) return;
    const col=mode==='input'?4:5,field=mode==='input'?'inputSizeNm':'reasoningSizeNm';
    let html='<div class="map-label">领域 / '+(mode==='input'?'输入':'推理')+'尺度 →</div>'+bins.map((b,i)=>`<div class="map-label scale-head"><strong>${b}</strong><small>${powers[i]}</small></div>`).join('');
    for(const [domain,label] of Object.entries(domains)){
      html+=`<div class="map-label domain">${label}</div>`;
      for(let i=0;i<4;i++){
        const tasks=framework.tasks.filter(t=>t[1]===domain&&t[col]===i&&(!ability||t[3]===ability)&&(!decision||reviewData.reviews[t[0]].decision===decision));
        const all=catalog.questions.filter(q=>(lifecycle==='all'||q.lifecycle===lifecycle)&&q.domain===domain&&inBin(q[field],i));
        const candidates=all.filter(q=>!ability||q.ability===ability);
        const passed=catalog.questions.filter(q=>q.lifecycle==='active'&&q.domain===domain&&inBin(q[field],i)&&q.prototypeScreeningPassed===true&&q.status==='pending_human_audit');
        const progress=mode==='reasoning'?`初筛 ${passed.length} / 目标 10`:`初筛分布 ${passed.length} · 非配额`;
        html+=`<div class="map-cell task-cell unified-cell"><div class="cell-progress"><b>${progress}</b><small>感知 ${passed.filter(q=>q.ability==='perception').length} · 推断 ${passed.filter(q=>q.ability==='inference').length} · 设计 ${passed.filter(q=>q.ability==='design').length}</small></div><div class="cell-label">实测候选 · ${candidates.length}</div>${candidates.length?candidates.map(q=>`<button class="task-chip ${abilities[q.ability][1]}" data-question="${esc(q.id)}"><small>${esc(q.id)} · ${esc(statuses[q.status]||q.status)}</small>${esc(q.title)}<span class="review-state">${q[field].toFixed(3)} nm</span></button>`).join(''):'<span class="map-gap">当前能力筛选下暂无实测候选</span>'}<details class="planned-tasks" ${tasks.length?'open':''}><summary>规划方向 · ${tasks.length}</summary>${tasks.map(t=>`<button class="task-chip ${abilities[t[3]][1]}" data-task-id="${t[0]}"><small>${t[0]} · ${abilities[t[3]][0]}</small>${esc(t[6])}<span class="review-state">首轮：${esc(reviewData.reviews[t[0]].decision_label)}<br>v0.4：${esc(readiness.reviews[t[0]].label)}</span></button>`).join('')||'<p class="map-gap">当前筛选下暂无规划方向</p>'}</details></div>`;
      }
    }
    $('#coverage').innerHTML=html;
    $('#framework-count').textContent=`${framework.tasks.filter(t=>(!ability||t[3]===ability)&&(!decision||reviewData.reviews[t[0]].decision===decision)).length} / 31 个规划方向`;
    const unlocated=catalog.questions.filter(q=>(lifecycle==='all'||q.lifecycle===lifecycle)&&(!ability||q.ability===ability)&&!bins.some((_,i)=>inBin(q[field],i)));
    $('#unlocated-list').innerHTML=unlocated.map(q=>`<button class="text-button" data-question="${esc(q.id)}">${esc(q.id)} · ${esc(q.title)}</button>`).join('');
    $('#unlocated-count').textContent=`待定位候选 ${unlocated.length} 条（当前尺度视角）`;
  };
  // Keep old candidate loading from overwriting the new task map.
  coverage=render;
  Promise.all(['data/task-framework.json','data/task-reviews.json','data/task-readiness-v04.json','data/catalog.json'].map(url=>fetch(url).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}))).then(([f,reviews,newReview,questions])=>{
    framework=f;
    reviewData=reviews;readiness=newReview;catalog=questions;
    const section=$('#coverage').closest('.section-block');
    section.querySelector('h2').textContent='任务方向与候选题，在一张地图里查看。';
    section.querySelector('.map-top p').textContent='科学领域 × 长度数量级';
    section.querySelector('.caption').textContent='规划方向使用拟议尺度，候选题使用实测尺度，二者不相互冒充。默认按推理尺度规划每格10道、各能力尽量3道。切换输入视角只改变分布，不重新定义配额。单元格进度为全能力统计，不随筛选变化；能力筛选同时影响方向与候选，处理建议只筛选规划方向。题库范围默认当前原型，重构、草案、历史可切换查看；初筛进度仅统计当前原型，不随题库范围变化。';
    const controls=document.createElement('div');
    controls.className='framework-controls';
    controls.innerHTML='<label>尺度视角 <select id="framework-mode"><option value="reasoning">解题推理尺度（默认）</option><option value="input">输入对象尺度</option></select></label><label>能力 <select id="framework-ability"><option value="">全部能力</option><option value="perception">感知</option><option value="inference">推断</option><option value="design">生成 / 设计</option></select></label><span id="framework-count"></span>';
    const reviewFilter=document.createElement('label');
    reviewFilter.innerHTML='处理建议 <select id="framework-decision"><option value="">全部建议</option><option value="priority">优先开展</option><option value="hold">保留待补</option><option value="rewrite">改写</option><option value="merge">合并</option><option value="defer">暂缓</option></select>';
    controls.querySelector('span').before(reviewFilter);
    const pool=document.createElement('label');pool.innerHTML='题库范围 <select id="framework-lifecycle"><option value="active">当前原型（默认）</option><option value="rework">待重构</option><option value="backlog">待材料草案</option><option value="archived">历史归档</option><option value="all">全部留存记录</option></select>';controls.querySelector('span').before(pool);
    section.querySelector('.map-scroll').before(controls);
    const summary=document.createElement('p');summary.className='review-summary';
    summary.innerHTML=`首轮来源查证 · ${esc(reviews.date)}<br>优先 ${reviews.counts.priority} · 待补 ${reviews.counts.hold} · 改写 ${reviews.counts.rewrite} · 合并 ${reviews.counts.merge} · 暂缓 ${reviews.counts.defer}。优先表示投入顺序，不表示 QA 已验证。<br><small>Q/C/M/B 是领域任务编号，数字仅为顺序；L/G/U/X/I 是旧候选的来源编号；CNM001–006 是本轮化学纳米尺度候选的顺序编号。卡片保留原提案，修改建议在详情中。</small> <a class="text-link" href="data/task-review.csv" download>下载查证表 ↓</a>`;
    controls.before(summary);
    $('#coverage').classList.add('framework-map');
    const footer=document.createElement('div');
    footer.innerHTML='<details class="unlocated"><summary id="unlocated-count"></summary><p class="caption">缺少统一实测值或不在当前显示范围内，不强行落点；点击可查看原记录。</p><div id="unlocated-list"></div></details>';
    section.append(footer);
    const screened=catalog.questions.filter(q=>q.lifecycle==='active'&&q.prototypeScreeningPassed===true&&q.status==='pending_human_audit').length;
    const latest=document.createElement('p');latest.className='review-summary';
    latest.innerHTML=`新版规则就绪审查 · ${esc(newReview.date)}<br>已有新版试跑方向 ${newReview.counts.instances_available} · 缺材料／评分器 ${newReview.counts.materials_or_scorer_missing} · 先修订题型 ${newReview.counts.definition_revision} · 设计暂不可执行 ${newReview.counts.evaluator_missing} · 合并方向 ${newReview.counts.merge}。<br>原型初筛 ${screened} / 160 · 正式可用 ${catalog.counts.ready}。这是方向级审查，未将31项都当作完整QA运行。<br><a class="text-link" href="data/task-readiness-v04.json" download>下载新版审查记录 ↓</a> · <a class="text-link" href="data/qa-disposition.md">逐题保留／重构／归档清单 ↗</a> · <a class="text-link" href="chem-local-batch.html">最新实际试跑报告 ↗</a>`;
    summary.after(latest);
    $('#framework-lifecycle').onchange=e=>{lifecycle=e.target.value;render()};
    $('#framework-mode').onchange=e=>{mode=e.target.value;render()};
    $('#framework-ability').onchange=e=>{ability=e.target.value;render()};
    $('#framework-decision').onchange=e=>{decision=e.target.value;render()};
    $('#coverage').addEventListener('click',e=>{
      const button=e.target.closest('[data-task-id]');if(!button)return;
      const t=f.tasks.find(t=>t[0]===button.dataset.taskId),r=reviews.reviews[t[0]];
      $('#detail-content').innerHTML=`<div class="eyebrow">${t[0]} / 规划方向 · 历史来源审查 ${esc(reviews.date)}</div><h2 id="detail-title">${esc(t[6])}</h2><p class="method-note">这是任务方向，不是完整试题。${readiness.reviews[t[0]].linked_candidates.length?'已有实例见下方按钮，可查看完整题目、附件和答案。':'当前尚无可作答实例，不能计入完成题量或人工审核队列。'} <a href="audit.html">统一标准与缺口统计 ↗</a></p><div class="detail-meta">${badge(t[3])}<span class="badge">${esc(domains[t[1]])} › ${esc(t[2])}</span><span class="badge">${esc(r.decision_label)}</span></div><p class="caption">原提案分类与规划位置：输入 ${bins[t[4]]}；推理 ${bins[t[5]]}。实例长度未核实。</p><div class="detail-section"><h3>新版 Builder v0.4 就绪审查</h3><p><b>${esc(readiness.reviews[t[0]].label)}</b><br>${esc(readiness.reviews[t[0]].reason)}</p><p>这是方向级材料与方法检查，不是该方向所有 QA 已通过。</p>${readiness.reviews[t[0]].linked_candidates.map(id=>`<button class="text-button" data-question="${id}">${id} · 完整题目 · 附件 · 答案</button>`).join(" ")}</div><div class="detail-section"><h3>处理理由 · ${esc(r.support_level)}</h3><p>${esc(r.reason)}</p><h3>下一动作</h3><p>${esc(r.next_action)}</p></div><div class="detail-section"><h3>原提案问法</h3><p>${esc(t[7])}</p><h3>查证后的构题建议</h3><p>${esc(r.construction)}</p><h3>验证方法</h3><p>${esc(r.verification)}</p><h3>所需输入</h3><p>${esc(t[8])}。${esc(r.input_assets)}。</p></div><div class="detail-section"><h3>具体来源与支持边界</h3>${r.source_ids.map(id=>{const s=reviews.sources[id];return `<div class="source-evidence"><a class="text-link" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a><p>定位：${esc(s.locator)}<br>${esc(s.finding)}</p></div>`}).join('')}<h3>现有候选</h3><p>${t[11]?esc(t[11])+'（状态不因本轮查证自动升级）':'尚无具体候选实例'}</p><p class="caption">${esc(r.benchmark_relation)} 首轮资料查证由助手完成，未经过独立领域审核；处理结论是研究建议。</p></div>`;
      $('#detail-dialog').showModal();
    });
    const scaleArticle=$('#method-scale');
    scaleArticle.innerHTML='<h2>01 / 两种尺度与数值横轴</h2><p>输入尺度描述给模型的对象范围；推理尺度描述解题需关注的范围。完整蛋白质的输入和原子接触的推理可以落在不同区间。</p><p>本版横轴显示 10⁻¹⁰、10⁻⁹、10⁻⁸、10⁻⁷、10⁻⁶ m 五个边界，即 0.1、1、10、100、1000 nm。等宽区间在对数轴上跨越一个数量级；这是研究规划窗口，不是对象类别的固定尺寸。超出范围的任务需扩展坐标轴。</p><p>有限分子的工作测量定义可采用所选原子集合的最大原子间距；局部任务采用任务所需子集。周期晶体需声明晶胞、超胞或实际关注范围，不能把无限晶体设为一个有限直径。必须先核实单位、坐标与协议，再填实例尺度。任务规划表中的位置均为拟议范围；同一单元格内的候选使用其已记录的实测尺度。</p><p><a class="text-link" href="https://www.bipm.org/en/measurement-units/si-prefixes" target="_blank" rel="noopener noreferrer">SI 前缀依据 ↗</a></p>';
    render();
  }).catch(e=>{$('#coverage').textContent='任务框架暂时无法载入，请刷新后重试。';console.error(e)});
})();
