'use strict';
(()=>{
 const $=id=>document.getElementById(id);let data,student,teacher;
 function render(){
  if(!data||!$('instance').value)return;
  teacher=data.teacher_answers.find(t=>t.numeric_id===$('instance').value);
  if(!teacher){$('choice-question').textContent='本例没有通过四选一生成，请查看批次失败记录。';$('choice-options').replaceChildren();$('download-choice').disabled=true;return;}
  student=data.student_packets.find(s=>s.id===teacher.id);$('download-choice').disabled=false;
  $('choice-question').textContent=student.question;$('choice-student').textContent=JSON.stringify(student,null,2);
  $('choice-teacher').textContent=JSON.stringify(teacher,null,2);$('choice-grade').textContent='';
  $('choice-options').replaceChildren(...student.options.map(o=>{const b=document.createElement('button');b.textContent=o.label+' · '+o.value+' Å';b.dataset.label=o.label;b.addEventListener('click',()=>{$('choice-grade').textContent=o.label===teacher.correct_label?'回答正确（仅选项评分，非人工审核）。':'回答错误。可以展开审核记录查看计算依据。'});return b}));
 }
 $('instance').addEventListener('change',render);
 new MutationObserver(render).observe($('instance'),{childList:true});
 $('download-choice').addEventListener('click',()=>{if(!student)return;const url=URL.createObjectURL(new Blob([JSON.stringify(student,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=student.id+'-student.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
 fetch('data/choice-workbench.json').then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{data=d;$('choice-summary').textContent=d.report.passed+' / '+d.report.attempted+' 通过程序检查 · 全部待人工审核 · 新增题库计数 0';$('choice-report').textContent=JSON.stringify(d.report,null,2);$('choice-code').textContent=d.code;render()}).catch(()=>{$('choice-summary').textContent='四选一记录加载失败，请刷新重试。'});
})();
