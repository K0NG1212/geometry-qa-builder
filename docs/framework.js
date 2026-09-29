/* The main atlas contains complete current candidates only. */
(()=>{
 let mode='reasoning',ability='';
 const bins=['0.1–1 nm','1–10 nm','10–100 nm','100–1000 nm'];
 const inside=(n,i)=>Number.isFinite(n)&&n>=10**(i-1)&&(n<10**i||(i===3&&n===1000));
 const section=$('#coverage').closest('.section-block');
 section.querySelector('h2').textContent='完整题目与真实缺口。';
 section.querySelector('.map-top p').textContent='4 个领域 × 4 个尺度';
 section.querySelector('.caption').textContent='按解题推理尺度统计；每格目标 10 道，感知 / 推断 / 设计各约 3 道。所有题目都已通过自动核验、仍待人工审核（见审核体系）。化学与量子 100–1000 nm 两格尚无题目，待与教授商定。';
 const controls=document.createElement('div');controls.className='framework-controls';
 controls.innerHTML='<label>能力 <select id="framework-ability"><option value="">全部能力</option><option value="perception">感知</option><option value="inference">推断</option><option value="design">生成 / 设计</option></select></label><span id="framework-count"></span>';
 section.querySelector('.map-scroll').before(controls);$('#coverage').classList.add('framework-map','compact-map');
 const render=()=>{
  if(!data)return;
  const rows=data.questions;
  let html='<div class="map-label">领域 / 推理尺度 →</div>'+bins.map(b=>`<div class="map-label scale-head"><strong>${b}</strong></div>`).join('');
  let capped=0;
  for(const [domain,label] of Object.entries(domains)){
   html+=`<div class="map-label domain">${label}</div>`;
   for(let i=0;i<4;i++){
    const all=rows.filter(q=>q.domain===domain&&inside(q.reasoningSizeNm,i));
    const n=all.length,c=k=>all.filter(q=>q.ability===k).length,sel=ability?c(ability):n;capped+=Math.min(n,10);
    const state=n===0?'empty':n>=10?(n>10?'over':'full'):'partial';
    const note=n===0?'尚无题目':n>10?`超额 ${n-10}（定稿时挑选）`:n===10?'已满':`缺 ${10-n}`;
    html+=`<button type="button" class="map-cell cov-cell ${state}" data-domain="${domain}" data-scale="${i}" data-ability="${ability}" aria-label="${label} ${bins[i]}：${n} 道，查看题目">
      <strong>${n} <span>/ 10</span></strong><em>${note}</em>
      <small><i class="p">感知 ${c('perception')}</i><i class="i">推断 ${c('inference')}</i><i class="d">设计 ${c('design')}</i></small>
      ${n?`<b>${ability?`查看${abilities[ability][0]} ${sel} 道 →`:'查看题目 →'}</b>`:''}</button>`;
   }
  }
  $('#coverage').innerHTML=html;
  $('#framework-count').textContent=`${rows.length} 道完整候选 · 每格按 10 道封顶的有效覆盖 ${capped} / 160 · 点击格子查看该格题目`;
 };
 coverage=render;$('#framework-ability').onchange=e=>{ability=e.target.value;render()};
 $('#method-scale').innerHTML='<h2>01 / 两种尺度与数值横轴</h2><p>推理尺度是解题实际需要理解的几何范围，决定原型配额；输入尺度描述给模型的整个对象。以 0.1、1、10、100、1000 nm 为区间边界。</p><p>每道题保存测量定义。有限结构可采用指定原子集合的最大中心距；具体使用全部原子还是重原子，见题目来源说明。不能仅凭对象名称推定尺寸。主图只展示完整实例的实测位置。</p>';
 render();
})();
