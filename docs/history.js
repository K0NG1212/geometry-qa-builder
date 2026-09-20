'use strict';
const area=document.createElement('section');area.className='section-block';area.innerHTML='<h2>历史规划方向</h2><p>以下31项是研究设想，不是试题，不计入当前题库。</p><div id="history-directions"></div>';document.querySelector('[data-view="questions"]').append(area);
Promise.all(['data/task-framework.json','data/task-reviews.json','data/task-readiness-v04.json'].map(u=>fetch(u).then(r=>r.json()))).then(([f,r,n])=>{
 document.querySelector('#history-directions').innerHTML=f.tasks.map(t=>`<details class="detail-section"><summary>${esc(t[0])} · ${esc(t[6])} · ${esc(n.reviews[t[0]].label)}</summary><p>原提案：${esc(t[7])}</p><p>所需材料：${esc(t[8])}</p><p>来源审查：${esc(r.reviews[t[0]].reason)}</p><p>后续：${esc(n.reviews[t[0]].next_action)}</p>${n.reviews[t[0]].linked_candidates.map(id=>`<p><a href="index.html?qa=${encodeURIComponent(id)}#questions">${esc(id)} · 查看实例记录 ↗</a></p>`).join('')}</details>`).join('');
}).catch(()=>{document.querySelector('#history-directions').textContent='历史目录载入失败。'});
