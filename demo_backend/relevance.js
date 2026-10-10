/* Reviewer-confirmed facts. Retrieved words never populate the form. */
let relevanceBusy = false;
const TW_LABELS = {counsel:'Counsel',interpretation:'Interpretation',defence_access:'Defence access',urgency:'Time sensitivity',opening:'Opening to act'};
const TW_OPENINGS = {monitoring:'Trial monitoring',legal_support:'Legal-support review',interpretation:'Interpretation follow-up',advocacy:'Evidence / advocacy review'};
const TW_FIELDS = {
  journalist_nexus:['Journalist / reporting connection',[['unknown','Unknown — verify'],['confirmed','Confirmed connection'],['absent','No journalist / reporting connection']],'BNS collection alone does not establish that a journalist is involved.'],
  case_stage:['Current court stage',[['unknown','Unknown — verify'],['ongoing','Ongoing proceedings'],['reopened','Reopened proceedings'],['appeal','Appeal / further review'],['completed','Proceedings completed']],'Completed proceedings can still have an advocacy or review opening.'],
  counsel:['Access to counsel',[['unknown','Unknown — verify'],['unavailable','Unavailable / denied'],['limited','Limited access'],['available','Available; no gap identified']],'25 points for an unavailable lawyer; 12.5 for limited access.'],
  interpretation:['Interpretation support',[['unknown','Unknown — verify'],['unavailable','Needed but unavailable / denied'],['limited','Provided with access gaps'],['available','Needed and adequately provided'],['not_required','Not required — verified']],'15 points for unmet need; 7.5 for limited support.'],
  defence_access:['Defence / evidence access',[['unknown','Unknown — verify'],['restricted','Restriction documented'],['adequate','No restriction identified']],'15 points for a documented access restriction.'],
  custody:['Currently in custody',[['unknown','Unknown — verify'],['yes','Yes — verified'],['no','No — verified']],'Custody contributes 20 urgency points; without counsel it triggers urgent review.'],
  immediate_threat:['Immediate safety threat',[['unknown','Unknown — verify'],['yes','Yes — documented'],['no','No known immediate threat — checked']],'A documented immediate threat triggers urgent review.'],
  deadline_status:['Next hearing / filing deadline',[['unknown','Unknown — verify'],['scheduled','Date confirmed'],['none','No upcoming deadline — checked']],'A deadline within 7 days triggers urgent review. Dates use India time.'],
  opening_status:['Practical opportunity to help',[['unknown','Unknown — verify'],['ready','Confirmed opening / route'],['to_arrange','Potential route to arrange'],['none','No current opening identified']],'20 points for a confirmed route; 10 for one to arrange. This does not assign TrialWatch resources.'],
  workflow_status:['TrialWatch review status',[['active','Keep review active / reopen'],['closed','Close review with a reason']],'A low score or a “No” misuse assessment never closes a review automatically.']
};

function relevanceBadge(r){return el('span',r.label,'tw-badge '+r.tier)}
function relevanceCell(r,c){
  const td=el('td',undefined,'relevance-cell'),block=el('div',undefined,'tw-cell'),status=el('div'),score=el('div',undefined,'tw-cell-score');
  status.append(el('span','TrialWatch priority','tw-cell-label'),relevanceBadge(r));
  score.append(el('strong',r.has_assessment&&!r.needs_recheck?r.score_display:'— /100'),el('small',!r.has_assessment?'Awaiting assessment':r.needs_recheck?'Recheck needed':r.coverage_percent+'% coverage'));
  const button=el('button',!r.has_assessment?'Assess priority':r.needs_recheck?'Recheck priority':'Edit priority','tw-assess');
  button.type='button';button.setAttribute('aria-label','Assess TrialWatch priority for '+pretty(c.title));button.onclick=()=>detail(c.cnr,true);
  block.append(status,score,button);td.append(block);td.title=r.action;return td;
}

function updateTrialwatchOverview(data){
  const counts=data.trialwatch_summary,reviews=data.relevance_review_summary;
  for(const key of ['urgent','high','routine','verify'])$('tw-count-'+key).textContent=counts[key];
  $('twOverviewNote').textContent=reviews.assessed===0?
    `No TrialWatch scores have been recorded yet. ${reviews.unassessed} cases need their support needs and intervention opening checked.`:
    `${reviews.assessed} relevance assessment(s) recorded · ${reviews.unassessed} awaiting assessment. Scores and tiers use checked support needs and intervention openings.`;
  $('twReviewNext').disabled=counts.verify===0;
}

async function assessNextTrialwatchCase(){
  const button=$('twReviewNext');button.disabled=true;
  try{const data=await api('/api/cases?sort=triage&trialwatch_tier=verify&limit=1');if(data.items.length)await detail(data.items[0].cnr,true);else await globalSummary()}
  catch(e){error(e)}finally{button.disabled=false}
}
function twField(key,facts){const [label,options,help]=TW_FIELDS[key],wrap=el('label',undefined,'tw-field');wrap.append(el('span',label));const select=el('select');select.id='tw-'+key;select.name=key;select.setAttribute('aria-label',label);for(const [value,text] of options){const opt=el('option',text);opt.value=value;select.append(opt)}select.value=facts[key];select.onchange=updateRelevanceForm;wrap.append(select,el('small',help));return wrap}

function renderRelevance(c){
  const r=c.trialwatch_relevance,facts=r.facts,card=el('div',undefined,'tw-card'),head=el('div',undefined,'tw-head'),title=el('div'),score=el('div',undefined,'tw-score');
  title.append(el('span','02 · TRIALWATCH PRIORITY','eyebrow'),el('h3','TrialWatch score & priority'),relevanceBadge(r));
  score.append(el('span','TRIALWATCH SCORE','tw-cell-label'),el('strong',r.has_assessment&&!r.needs_recheck?r.score_display:'— /100'),el('small',!r.has_assessment?'Awaiting assessment':r.needs_recheck?'Recheck needed':r.coverage_percent+'% assessed coverage'));
  head.append(title,score);card.append(head,el('p',r.action,'tw-action'));
  if(r.has_assessment){const reasons=el('div',undefined,'tw-reasons');for(const reason of r.reasons.slice(0,5))reasons.append(el('span',reason));card.append(reasons)}
  else card.append(el('p','Confirm journalist connection, support needs and an opening to act. Nothing is inferred from a missing detail in a court order.','review-help'));
  const breakdown=el('div',undefined,'tw-breakdown');for(const f of r.factors){const block=el('div',undefined,'tw-factor');block.append(el('small',TW_LABELS[f.key]),el('b',f.assessed?f.range[0]+'/'+f.max:'— /'+f.max));breakdown.append(block)}card.append(breakdown);
  const editor=el('details',undefined,'tw-editor');editor.id='twEditor';editor.append(el('summary',r.has_assessment?r.needs_recheck?'Recheck TrialWatch priority':'Edit TrialWatch priority':'Assess TrialWatch priority'));
  const form=el('form',undefined,'tw-form');form.id='twForm';form.onsubmit=e=>{e.preventDefault();submitRelevance()};
  for(const [label,keys] of [['Case fit',['journalist_nexus','case_stage']],['Fair-trial support needs',['counsel','interpretation','defence_access']],['Timing & safety',['custody','immediate_threat','deadline_status']],['An opening to act',['opening_status']]]){
    const group=el('fieldset'),grid=el('div',undefined,'tw-grid');group.append(el('legend',label));for(const key of keys)grid.append(twField(key,facts));group.append(grid);
    if(keys.includes('deadline_status')){const wrap=el('label',undefined,'tw-field');wrap.id='twDateWrap';wrap.append(el('span','Confirmed next deadline'));const input=el('input');input.id='tw-next_deadline';input.type='date';input.value=facts.next_deadline||'';input.min=r.as_of;input.setAttribute('aria-label','Confirmed next deadline');wrap.append(input);grid.append(wrap)}
    if(keys.includes('opening_status')){const choices=el('div',undefined,'tw-openings');choices.id='twOpenings';choices.setAttribute('role','group');choices.setAttribute('aria-label','Intervention openings');for(const [key,text] of Object.entries(TW_OPENINGS)){const label=el('label',undefined,'tw-opening'),input=el('input');input.type='checkbox';input.name='twOpening';input.value=key;input.checked=facts.openings.includes(key);input.setAttribute('aria-label',text);label.append(input,el('span',text));choices.append(label)}group.append(choices)}
    form.append(group);
  }
  const noteLabel=el('label',undefined,'tw-field');noteLabel.append(el('span','Source note for your checked facts'));const note=el('textarea');note.id='tw-evidence_note';note.maxLength=2000;note.rows=3;note.value=facts.evidence_note;note.placeholder='Order/date/page or other checked source for each confirmed entry. Distinguish the defendant’s counsel from other parties’ counsel.';note.setAttribute('aria-label','Source note for your checked facts');noteLabel.append(note,el('small','Required when you confirm facts. Leave undocumented facts unknown.'));form.append(noteLabel);
  if(c.relevance_passages.length){const sources=el('details',undefined,'tw-sources');sources.append(el('summary','Passages to inspect · '+c.relevance_passages.length),el('p','Keyword matches are reading aids, not findings. An advocate may represent another party; “translation” can refer to a document. Inspect the full order and confirm the relevant person and current status.'));for(const q of c.relevance_passages){const passage=el('div',undefined,'tw-passage');passage.append(el('b',q.topic+' · '+date(q.order_date)+' · page '+q.page),el('blockquote',q.quote),linkButton('Read source order ↗',q.pdf_url,true));sources.append(passage)}form.append(sources)}
  const workflow=el('fieldset'),grid=el('div',undefined,'tw-grid');workflow.append(el('legend','Review workflow'));grid.append(twField('workflow_status',facts));const reasonLabel=el('label',undefined,'tw-field');reasonLabel.id='twCloseWrap';reasonLabel.append(el('span','Reason for closing this review'));const reason=el('textarea');reason.id='tw-close_reason';reason.maxLength=1000;reason.rows=2;reason.value=facts.close_reason;reason.setAttribute('aria-label','Reason for closing this review');reasonLabel.append(reason);grid.append(reasonLabel);workflow.append(grid);form.append(workflow);
  const actions=el('div',undefined,'review-actions'),save=el('button','Save relevance','btn primary');save.id='twSave';save.type='submit';actions.append(save);form.append(actions);
  const message=el('div',undefined,'review-message');message.id='twMessage';message.setAttribute('role','status');message.setAttribute('aria-live','polite');form.append(message);editor.append(form);card.append(editor);
  card.append(el('p',r.has_assessment?'Last saved '+datetime(r.updated_at)+'. Unknown facts contribute a range. Source changes require recheck.':'Separate from the law score and misuse assessment. Provisional team rubric; no guarantee of intervention.','tw-foot'));
  $('trialwatchReview').replaceChildren(card);updateRelevanceForm();
}

function updateRelevanceForm(){
  if(!$('twForm'))return;
  const scheduled=$('tw-deadline_status').value==='scheduled';$('twDateWrap').hidden=!scheduled;$('tw-next_deadline').required=scheduled;
  $('twOpenings').hidden=!['ready','to_arrange'].includes($('tw-opening_status').value);
  const closed=$('tw-workflow_status').value==='closed';$('twCloseWrap').hidden=!closed;$('tw-close_reason').required=closed;
  for(const input of $('twForm').querySelectorAll('input,select,textarea,button'))input.disabled=relevanceBusy;
  $('twSave').textContent=relevanceBusy?'Saving…':'Save relevance';
}

function relevanceDraft(){
  const facts={};for(const key of Object.keys(TW_FIELDS))facts[key]=$('tw-'+key).value;
  facts.next_deadline=facts.deadline_status==='scheduled'?$('tw-next_deadline').value||null:null;
  facts.openings=['ready','to_arrange'].includes(facts.opening_status)?[...document.querySelectorAll('input[name=twOpening]:checked')].map(n=>n.value):[];
  facts.evidence_note=$('tw-evidence_note').value.trim();facts.close_reason=facts.workflow_status==='closed'?$('tw-close_reason').value.trim():'';
  return facts;
}

async function submitRelevance(){
  if(relevanceBusy||!currentCase)return;
  const c=currentCase,cnr=c.cnr,body={...relevanceDraft(),expected_revision:c.trialwatch_relevance.revision,evidence_version:c.review_evidence_version};
  relevanceBusy=true;updateRelevanceForm();$('twMessage').textContent='';
  try{
    const updated=await api('/api/cases/'+encodeURIComponent(cnr)+'/relevance',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    relevanceBusy=false;
    if(currentCase?.cnr===cnr&&$('detail').open){renderCase(updated);$('twEditor').open=true;$('twMessage').textContent='Relevance saved. Queue updated; the law score is unchanged.'}
    await Promise.all([status(),list(),globalSummary()]);
  }catch(e){
    relevanceBusy=false;
    if(currentCase?.cnr===cnr){updateRelevanceForm();const message=$('twMessage');message.classList.add('error');message.replaceChildren(el('span',e.message));if(e.status===409){const reload=el('button','Reload current case','review-reload');reload.type='button';reload.onclick=()=>detail(cnr);message.append(reload)}}
  }
}
