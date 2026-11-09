/* The main atlas contains complete current candidates only. */
(()=>{
 let mode='reasoning',ability='';
 // The three ability names and the hover sentence, in both languages: i18n.js matches whole strings and
 // these carry a count, so they are built here rather than left for the dictionary (see pixelmap.js).
 let EN=true; try{EN=(localStorage.getItem('geobench-lang')||'en')==='en'}catch(e){}
 const ABILITY=EN?{perception:'Perception',inference:'Inference',design:'Design'}
                 :{perception:'感知',inference:'推断',design:'设计'};
 const FULL=EN?{perception:'Perception',inference:'Inference',design:'Generation / design'}
              :{perception:'感知',inference:'推断',design:'生成 / 设计'};
 const share=(key,v,total)=>EN
   ?`${FULL[key]}: ${v} of ${total} questions in this cell (${total?Math.round(v/total*100):0}%)`
   :`${FULL[key]}：这一格 ${total} 道里的 ${v} 道（${total?Math.round(v/total*100):0}%）`;
 const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
 const bins=['0.1–1 nm','1–10 nm','10–100 nm','100–1000 nm'];
 const inside=(n,i)=>Number.isFinite(n)&&n>=10**(i-1)&&(n<10**i||(i===3&&n===1000));
 const section=$('#coverage').closest('.section-block');
 section.querySelector('h2').textContent='四个领域 × 四个尺度（总览）。';
 section.querySelector('.map-top p').textContent='4 个领域 × 4 个尺度';
 const captionBase='按解题推理尺度统计。每格 10 道是 160 道原型期的配额，题库已经扩到这个数的数倍，所以这里只当总览看；真正planned against的坐标系是下面那张按子领域细分的。所有题目都已通过程序核验与独立检查器，仍待人工审核。';section.querySelector('.caption').textContent=captionBase;
 const legendBox=section.querySelector('.legend');
 if(legendBox)legendBox.outerHTML='<div class="legend ability-key">'+
   [['p','perception'],['i','inference'],['d','design']]
     .map(([cls,k])=>`<b title="${FULL[k]}"><i class="${cls}"></i>${ABILITY[k]}</b>`).join('')+'</div>';
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
    const note=n===0?'尚无题目':'';
    const split=[['p','perception'],['i','inference'],['d','design']].map(([cls,ab])=>({cls,ab,n:c(ab)}));
    const pct=v=>n?Math.round(v/n*100):0;
    const chip=s=>`<i class="${s.cls}" title="${esc(share(s.ab,s.n,n))}">${esc(ABILITY[s.ab])} ${s.n}</i>`;
    const bar=n?`<div class="ability-bar" title="${esc(split.map(s=>`${ABILITY[s.ab]} ${pct(s.n)}%`).join(' · '))}">`+
      split.map(s=>s.n?`<span class="${s.cls}" style="flex:${s.n}"></span>`:'').join('')+'</div>':'';
    html+=`<button type="button" class="map-cell cov-cell ${state}" data-domain="${domain}" data-scale="${i}" data-ability="${ability}" aria-label="${label} ${bins[i]}：${n} 道，查看题目">
      <strong>${n}</strong><em>${note}</em>
      ${bar}
      <small>${split.map(chip).join('')}</small>
      ${n?`<b>${ability?`查看${abilities[ability][0]} ${sel} 道 →`:'查看题目 →'}</b>`:''}</button>`;
   }
  }
  $('#coverage').innerHTML=html;
  $('#framework-count').textContent=`${rows.length} 道题 · 点击格子查看该格题目（细分到子领域的坐标系见下一张图）`;
  const empty=$('#coverage').querySelectorAll('.cov-cell.empty').length;section.querySelector('.caption').textContent=captionBase+(empty?` 目前有 ${empty} 格尚无题目。`:'');
 };
 coverage=render;$('#framework-ability').onchange=e=>{ability=e.target.value;render()};
 const scaleBlock=$('#method-scale');
 if(scaleBlock)scaleBlock.innerHTML=(EN
  ?'<h2>01 / Two scales and the numeric axis</h2>'+
   '<p>The reasoning scale is the geometric range a question actually requires, and it sets the prototype quota; '+
   'the input scale describes the whole object handed to the model. The bin edges are 0.1, 1, 10, 100 and 1000 nm.</p>'+
   '<p><b>Why it starts at 0.1 nm:</b> 0.1 nm is 1 angstrom, the length of a covalent bond (C-C about 0.154 nm). '+
   'One decade below, at 0.01 nm, nothing is left but nuclei and core electrons, and every source used here gives '+
   'atomic positions only. <b>Why it stops at 1000 nm:</b> 1000 nm is 1 micrometre, the first decade above visible '+
   'light (400-700 nm), where the largest objects collected here \u2014 photonic crystals, cholesteric phases \u2014 have '+
   'their periods. A decade further up there are no atomic coordinates to reason over. <b>Why decades:</b> the range '+
   'spans four orders of magnitude, so equal steps would push almost every question into the first bin.</p>'+
   '<p>Every question stores its measurement definition. For a finite structure it can be the largest centre-to-centre '+
   'distance over a named atom set; whether all atoms or heavy atoms are used is stated in the question\u2019s source note. '+
   'Size cannot be inferred from the name of an object. The main map shows measured positions of complete instances only.</p>'+
   '<p><a class="text-link" href="legend.html#scales">Full reasoning for the axis bounds \u2197</a></p>'
  :'<h2>01 / 两种尺度与数值横轴</h2>'+
   '<p>推理尺度是解题实际需要理解的几何范围，决定原型配额；输入尺度描述给模型的整个对象。以 0.1、1、10、100、1000 nm 为区间边界。</p>'+
   '<p><b>为什么从 0.1 nm 起：</b>0.1 nm = 1 Å，正好是共价键长的量级（C\u2013C 约 0.154 nm）。再往下一个十倍是 0.01 nm，'+
   '那里只剩原子核与内层电子，而本库所有来源给的都只是原子位置。<b>为什么到 1000 nm 止：</b>1000 nm = 1 µm，是可见光波长'+
   '（400\u2013700 nm）往上的第一个十倍，本库最大的对象（光子晶体、胆甾相）的周期正好落在这一格；再往上一个十倍就没有'+
   '原子坐标可推理了。<b>为什么按十倍分：</b>整个范围跨四个数量级，等分会把几乎所有题挤进第一格。</p>'+
   '<p>每道题保存测量定义。有限结构可采用指定原子集合的最大中心距；具体使用全部原子还是重原子，见题目来源说明。'+
   '不能仅凭对象名称推定尺寸。主图只展示完整实例的实测位置。</p>'+
   '<p><a class="text-link" href="legend.html#scales">尺度边界的完整理由 \u2197</a></p>');
 // A deep link, a map cell or the section list may point into a folded section (B6). Opening it here keeps
 // every existing anchor working: route() still scrolls, it just no longer scrolls to something collapsed.
 const openFold=()=>{const id=location.hash.slice(1);if(!id)return;
  const el=document.getElementById(id)||document.querySelector('[name="'+id+'"]');
  const fold=el&&el.closest&&el.closest('details');if(fold)fold.open=true};
 addEventListener('hashchange',openFold);
 document.addEventListener('click',()=>setTimeout(openFold,0));
 openFold();
 render();
})();
