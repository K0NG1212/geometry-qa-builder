/* The main atlas contains complete current candidates only. */
(()=>{
 let mode='reasoning',ability='';
 const bins=['0.1–1 nm','1–10 nm','10–100 nm','100–1000 nm'];
 const inside=(n,i)=>Number.isFinite(n)&&n>=10**(i-1)&&(n<10**i||(i===3&&n===1000));
 const section=$('#coverage').closest('.section-block');
 section.querySelector('h2').textContent='完整题目与真实缺口。';
 section.querySelector('.map-top p').textContent='4 个领域 × 4 个尺度';
 section.querySelector('.caption').textContent='每格目标10道，各能力尽量3道。默认按推理尺度统计配额；输入尺度只展示分布。能力筛选只改变可见题目，不改变总进度。空格表示尚无完整候选，所有候选仍待独立审核。';
 const controls=document.createElement('div');controls.className='framework-controls';
 controls.innerHTML='<label>尺度视角 <select id="framework-mode"><option value="reasoning">解题推理尺度（默认）</option><option value="input">输入对象尺度</option></select></label><label>能力 <select id="framework-ability"><option value="">全部能力</option><option value="perception">感知</option><option value="inference">推断</option><option value="design">生成 / 设计</option></select></label><span id="framework-count"></span>';
 section.querySelector('.map-scroll').before(controls);$('#coverage').classList.add('framework-map');
 const render=()=>{
  if(!data)return;
  const rows=data.questions,field=mode==='reasoning'?'reasoningSizeNm':'inputSizeNm';
  let html='<div class="map-label">领域 / '+(mode==='reasoning'?'推理':'输入')+'尺度 →</div>'+bins.map(b=>`<div class="map-label scale-head"><strong>${b}</strong></div>`).join('');
  for(const [domain,label] of Object.entries(domains)){
   html+=`<div class="map-label domain">${label}</div>`;
   for(let i=0;i<4;i++){
    const all=rows.filter(q=>q.domain===domain&&inside(q[field],i)),shown=all.filter(q=>!ability||q.ability===ability);
    const progress=mode==='reasoning'?`初筛 ${all.length} / 10 · 缺 ${Math.max(0,10-all.length)}`:`输入分布 ${all.length} · 非配额`;
    html+=`<div class="map-cell task-cell unified-cell"><div class="cell-progress"><b>${progress}</b><small>感知 ${all.filter(q=>q.ability==='perception').length} · 推断 ${all.filter(q=>q.ability==='inference').length} · 设计 ${all.filter(q=>q.ability==='design').length}</small></div>${shown.map(q=>`<button class="task-chip ${abilities[q.ability][1]}" data-question="${esc(q.id)}"><small>${esc(q.id)} · ${esc(abilities[q.ability][0])}</small>${esc(q.title)}<span class="review-state">${q[field].toFixed(3)} nm · 待人工审核</span></button>`).join('')||`<p class="map-gap">${all.length?'当前能力筛选下暂无题目':'待构题 · 尚无完整候选'}</p>`}</div>`;
   }
  }
  $('#coverage').innerHTML=html;$('#framework-count').textContent=`${rows.filter(q=>!ability||q.ability===ability).length} / ${rows.length} 道完整候选`;
 };
 coverage=render;$('#framework-mode').onchange=e=>{mode=e.target.value;render()};$('#framework-ability').onchange=e=>{ability=e.target.value;render()};
 $('#method-scale').innerHTML='<h2>01 / 两种尺度与数值横轴</h2><p>推理尺度是解题实际需要理解的几何范围，决定原型配额；输入尺度描述给模型的整个对象。以 0.1、1、10、100、1000 nm 为区间边界。</p><p>每道题保存测量定义。有限结构可采用指定原子集合的最大中心距；具体使用全部原子还是重原子，见题目来源说明。不能仅凭对象名称推定尺寸。主图只展示完整实例的实测位置。</p>';
 render();
})();
