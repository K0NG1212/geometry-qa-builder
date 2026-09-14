/* Task framework is separate from instantiated QA and candidate counts. */
(() => {
  let framework;
  let reviewData;
  let decision = '';
  let mode = 'input';
  let ability = '';
  const bins = ['0.1–1 nm','1–10 nm','10–100 nm','100–1000 nm'];
  const powers = ['10⁻¹⁰–10⁻⁹ m','10⁻⁹–10⁻⁸ m','10⁻⁸–10⁻⁷ m','10⁻⁷–10⁻⁶ m'];
  const render = () => {
    if (!framework) return;
    const col = mode === 'input' ? 4 : 5;
    let html = '<div class="map-label">学科 / 参考尺度 →</div>' + bins.map((b,i)=>`<div class="map-label scale-head"><strong>${b}</strong><small>${powers[i]}</small></div>`).join('');
    for (const [domain,label] of Object.entries(domains)) {
      html += `<div class="map-label domain">${label}</div>`;
      for (let i=0;i<4;i++) {
        const rows=framework.tasks.filter(t=>t[1]===domain&&t[col]===i&&(!ability||t[3]===ability)&&(!decision||reviewData.reviews[t[0]].decision===decision));
        html += `<div class="map-cell task-cell">${rows.length?rows.map(t=>`<button class="task-chip ${abilities[t[3]][1]}" data-task-id="${t[0]}"><small>${t[0]} · ${abilities[t[3]][0]}</small>${esc(t[6])}<span class="review-state">${esc(reviewData.reviews[t[0]].decision_label)}</span></button>`).join(''):'<span class="map-gap">当前条件下无条目<br>可切换筛选查看</span>'}</div>`;
      }
    }
    $('#coverage').innerHTML=html;
    renderMeasured();
    $('#framework-count').textContent=`${framework.tasks.filter(t=>(!ability||t[3]===ability)&&(!decision||reviewData.reviews[t[0]].decision===decision)).length} / 31 个方向 · 规划位置`;
  };
  function renderMeasured(){
    const target=$('#measured-coverage');if(!target||!data)return;
    const rows=data.questions.filter(q=>Number.isFinite(q.inputSizeNm)&&(!ability||q.ability===ability));
    const field=mode==='input'?'inputSizeNm':'reasoningSizeNm';
    let html='<div class="map-label">实测候选 / '+(mode==='input'?'输入':'推理')+'尺度 →</div>'+bins.map(b=>`<div class="map-label">${b}</div>`).join('');
    for(const [domain,label] of Object.entries(domains)){
      html+=`<div class="map-label domain">${label}</div>`;
      for(let i=0;i<4;i++){
        const lo=10**(i-1),hi=10**i;
        const selected=rows.filter(q=>q.domain===domain&&q[field]>=lo&&(q[field]<hi||(i===3&&q[field]===hi)));
        html+=`<div class="map-cell task-cell">${selected.length?selected.map(q=>`<button class="task-chip p" data-question="${esc(q.id)}"><small>${esc(q.id)} · 待人工审核</small>${esc(q.title)}<span>${q[field].toFixed(3)} nm</span></button>`).join(''):'<span class="map-gap">暂无实测实例</span>'}</div>`;
      }
    }
    target.innerHTML=html;
  }
  // Keep old candidate loading from overwriting the new task map.
  coverage=render;
  Promise.all(['data/task-framework.json','data/task-reviews.json'].map(url=>fetch(url).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}))).then(([f,reviews])=>{
    framework=f;
    reviewData=reviews;
    const section=$('#coverage').closest('.section-block');
    section.querySelector('h2').textContent='从任务类型，展开研究版图。';
    section.querySelector('.map-top p').textContent='科学领域 × 长度数量级';
    section.querySelector('.caption').textContent='等宽区间对应 log₁₀ 长度轴；左闭右开，最右端包含 1000 nm。1 Å = 0.1 nm，1 nm = 10⁻⁹ m，1 μm = 1000 nm。任务按拟议情境放置，具体对象尺寸可跨区间；原有 26 条候选尚无统一实测值；新增 6 条的实测位置见下方独立实例图。';
    const controls=document.createElement('div');
    controls.className='framework-controls';
    controls.innerHTML='<label>尺度视角 <select id="framework-mode"><option value="input">输入对象尺度</option><option value="reasoning">解题推理尺度</option></select></label><label>能力 <select id="framework-ability"><option value="">全部能力</option><option value="perception">感知</option><option value="inference">推断</option><option value="design">生成 / 设计</option></select></label><span id="framework-count"></span>';
    const reviewFilter=document.createElement('label');
    reviewFilter.innerHTML='处理建议 <select id="framework-decision"><option value="">全部建议</option><option value="priority">优先开展</option><option value="hold">保留待补</option><option value="rewrite">改写</option><option value="merge">合并</option><option value="defer">暂缓</option></select>';
    controls.querySelector('span').before(reviewFilter);
    section.querySelector('.map-scroll').before(controls);
    const summary=document.createElement('p');summary.className='review-summary';
    summary.innerHTML=`首轮来源查证 · ${esc(reviews.date)}<br>优先 ${reviews.counts.priority} · 待补 ${reviews.counts.hold} · 改写 ${reviews.counts.rewrite} · 合并 ${reviews.counts.merge} · 暂缓 ${reviews.counts.defer}。优先表示投入顺序，不表示 QA 已验证。<br><small>Q/C/M/B 是领域任务编号，数字仅为顺序；L/G/U/X/I 是旧候选的来源编号；CNM001–006 是本轮化学纳米尺度候选的顺序编号。卡片保留原提案，修改建议在详情中。</small> <a class="text-link" href="data/task-review.csv" download>下载查证表 ↓</a>`;
    controls.before(summary);
    $('#coverage').classList.add('framework-map');
    const measured=document.createElement('div');
    measured.innerHTML='<h3>已有实测位置的候选 · 6 道公开试跑示例</h3><p class="caption">与上方 31 个规划方向分别统计。沿用上方尺度视角与能力筛选；任务优先级筛选不适用于本图。仅覆盖 1.44–1.83 nm 的输入；尺度采用最大重原子中心距，局部任务采用指定子集。旧 26 条因缺少统一实测值暂不落点。<a class="text-link" href="pilot-chem.html">本轮来源与检查报告 ↗</a></p><div class="map-scroll"><div id="measured-coverage" class="framework-map"></div></div>';
    section.append(measured);
    $('#framework-mode').onchange=e=>{mode=e.target.value;render()};
    $('#framework-ability').onchange=e=>{ability=e.target.value;render()};
    $('#framework-decision').onchange=e=>{decision=e.target.value;render()};
    $('#coverage').addEventListener('click',e=>{
      const button=e.target.closest('[data-task-id]');if(!button)return;
      const t=f.tasks.find(t=>t[0]===button.dataset.taskId),r=reviews.reviews[t[0]];
      $('#detail-content').innerHTML=`<div class="eyebrow">${t[0]} / SOURCE REVIEW · ${esc(reviews.date)}</div><h2 id="detail-title">${esc(t[6])}</h2><div class="detail-meta">${badge(t[3])}<span class="badge">${esc(domains[t[1]])} › ${esc(t[2])}</span><span class="badge">${esc(r.decision_label)}</span></div><p class="caption">原提案分类与规划位置：输入 ${bins[t[4]]}；推理 ${bins[t[5]]}。实例长度未核实。</p><div class="detail-section"><h3>处理理由 · ${esc(r.support_level)}</h3><p>${esc(r.reason)}</p><h3>下一动作</h3><p>${esc(r.next_action)}</p></div><div class="detail-section"><h3>原提案问法</h3><p>${esc(t[7])}</p><h3>查证后的构题建议</h3><p>${esc(r.construction)}</p><h3>验证方法</h3><p>${esc(r.verification)}</p><h3>所需输入</h3><p>${esc(t[8])}。${esc(r.input_assets)}。</p></div><div class="detail-section"><h3>具体来源与支持边界</h3>${r.source_ids.map(id=>{const s=reviews.sources[id];return `<div class="source-evidence"><a class="text-link" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)} ↗</a><p>定位：${esc(s.locator)}<br>${esc(s.finding)}</p></div>`}).join('')}<h3>现有候选</h3><p>${t[11]?esc(t[11])+'（状态不因本轮查证自动升级）':'尚无具体候选实例'}</p><p class="caption">${esc(r.benchmark_relation)} 首轮资料查证由助手完成，未经过独立领域审核；处理结论是研究建议。</p></div>`;
      $('#detail-dialog').showModal();
    });
    const scaleArticle=$('#method-scale');
    scaleArticle.innerHTML='<h2>01 / 两种尺度与数值横轴</h2><p>输入尺度描述给模型的对象范围；推理尺度描述解题需关注的范围。完整蛋白质的输入和原子接触的推理可以落在不同区间。</p><p>本版横轴显示 10⁻¹⁰、10⁻⁹、10⁻⁸、10⁻⁷、10⁻⁶ m 五个边界，即 0.1、1、10、100、1000 nm。等宽区间在对数轴上跨越一个数量级；这是研究规划窗口，不是对象类别的固定尺寸。超出范围的任务需扩展坐标轴。</p><p>有限分子的工作测量定义可采用所选原子集合的最大原子间距；局部任务采用任务所需子集。周期晶体需声明晶胞、超胞或实际关注范围，不能把无限晶体设为一个有限直径。必须先核实单位、坐标与协议，再填实例尺度。任务规划表中的位置均为拟议范围；实测实例图另行展示已有测量协议的候选。</p><p><a class="text-link" href="https://www.bipm.org/en/measurement-units/si-prefixes" target="_blank" rel="noopener noreferrer">SI 前缀依据 ↗</a></p>';
    render();
  }).catch(e=>{$('#coverage').textContent='任务框架暂时无法载入，请刷新后重试。';console.error(e)});
})();
