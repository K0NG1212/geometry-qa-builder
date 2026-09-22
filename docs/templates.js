'use strict';
(()=>{
 const $=id=>document.getElementById(id),esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let data,current;
 const states={implemented:'已接通 · 本轮运行',existing_legacy:'已有底层实现 · 待迁移',planned:'已定义路线 · 未实现',blocked:'缺评价器 · 暂不开放'};
 function render(){
  current=data.report.items.find(x=>x.id===$('instance').value);
  const student=data.student_packets.find(x=>x.id===current.id);
  $('instance-meta').textContent=current.id+' · '+current.atom_count+' 个原子 · 来源原题 '+current.qa_id;
  $('student-question').textContent=student.question;$('student-scope').textContent=student.scope;
  $('xyz').textContent=student.input.text;$('student-json').textContent=JSON.stringify(student,null,2);
  $('teacher-json').textContent=JSON.stringify(current.short_answer,null,2);$('verification').textContent=JSON.stringify(current,null,2);
  $('response').value='';$('live-result').textContent='';$('grade-result').textContent='';
 }
 $('recompute').addEventListener('click',()=>{
  try{
   const text=data.student_packets.find(x=>x.id===current.id).input.text;
   const lines=text.trimEnd().split(/\r?\n/),n=Number(lines[0]);
   const points=lines.slice(2).filter(s=>s.trim()).map(s=>s.trim().split(/\s+/).slice(1).map(Number));
   if(points.length!==n||n<2||points.some(p=>p.length!==3||p.some(v=>!Number.isFinite(v))))throw Error('输入无效');
   let result;
   if(current.template==='global_extent'){result=0;for(let i=0;i<n;i++)for(let j=0;j<i;j++)result=Math.max(result,Math.hypot(...points[i].map((v,k)=>v-points[j][k])))}
   else{const c=[0,1,2].map(k=>points.reduce((s,p)=>s+p[k],0)/n);result=Math.sqrt(points.reduce((s,p)=>s+p.reduce((a,v,k)=>a+(v-c[k])**2,0),0)/n)}
   const same=Math.abs(result-current.computed)<1e-8;
   $('live-result').textContent=result.toFixed(4)+' Å · '+(same?'与保存的 Python 数值一致':'与 Python 记录不一致，需检查');
  }catch(e){$('live-result').textContent=e.message}
 });
 $('grade').addEventListener('click',()=>{
  const text=$('response').value,v=Number(text),a=current.short_answer;
  $('grade-result').textContent=!text||!Number.isFinite(v)?'请输入有限数值。':Math.abs(v-a.value)<=a.absolute_tolerance?'通过数值评分（非科学质量审核）':'未通过：与四位小数参考值的误差超过容差。';
 });
 $('download-student').addEventListener('click',()=>{const student=data.student_packets.find(x=>x.id===current.id);const url=URL.createObjectURL(new Blob([JSON.stringify(student,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=current.id+'-student.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
 $('instance').addEventListener('change',render);
 fetch('data/template-workbench.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{
  data=d;$('result-count').textContent=d.report.passed+' / '+d.report.count;
  $('families').innerHTML=d.registry.templates.map(t=>`<article><span class="state">${esc(states[t.status])}</span><h3>${esc(t.name)}</h3><p><b>输入：</b>${esc(t.inputs)}</p><p><b>方法：</b>${esc(t.principle)}</p><details><summary>验证方式与限制</summary><p>${esc(t.validation)}</p><p>${esc(t.limits)}</p><p>${esc(t.template_review)}</p></details></article>`).join('');
  $('instance').innerHTML=d.report.items.map(x=>`<option value="${esc(x.id)}">${esc(x.qa_id)} · ${x.template==='global_extent'?'最大间距':'回转半径'} · ${x.atom_count} 个原子</option>`).join('');
  $('batch-rows').innerHTML=d.report.items.map(x=>`<tr><td><a href="index.html?qa=${encodeURIComponent(x.qa_id)}#questions">${esc(x.qa_id)}</a></td><td>${x.template==='global_extent'?'最大间距':'回转半径'}</td><td>${x.atom_count}</td><td>${x.status==='numeric_verified'?'通过':'待修订'}</td></tr>`).join('');
  $('calculator-code').textContent=d.code;render();
 }).catch(()=>{$('load-error').hidden=false});
})();
