/* Automatic evidence assessment + independent reviewer fit feedback. */
let relevanceBusy=false, assessmentBusy=false, assessmentDraft={misuse:null,fit:null};
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

const QUEUE_LABELS={urgent:'Immediate review',high:'Focus first',review:'Review',monitor:'Monitor',verify:'Check evidence',closed:'Closed review',outside_scope:'Referral'};
function queueBadge(p){return el('span',p.label,'queue-badge '+p.band)}
function priorityCell(c){
  const p=c.case_priority,td=el('td',undefined,'unified-priority-cell'),head=el('div',undefined,'priority-line');
  head.append(queueBadge(p),el('b',p.score_display,'queue-score'));td.append(head,el('small','Law '+p.law_score_display+' · Fit '+p.fit_score_display,'priority-inputs'));return td;
}
function updateTrialwatchOverview(data){
  const summary=data.queue_summary,counts=summary.counts,total=summary.total;
  $('highCount').textContent=counts.high+counts.urgent;
  $('reviewProgress').textContent=summary.reviewed+' reviewed';
  $('distributionLabel').textContent=total+' '+(DEMO_MODE?'demo scenarios':'cases')+' · '+(counts.high+counts.urgent)+' to focus on';
  const bar=$('priorityDistribution');bar.replaceChildren();
  for(const key of ['urgent','high','review','monitor','verify','closed','outside_scope'])if(counts[key]){const seg=el('button',undefined,'distribution-segment '+key);seg.type='button';seg.style.flexGrow=counts[key];seg.title=QUEUE_LABELS[key]+': '+counts[key];seg.setAttribute('aria-label',QUEUE_LABELS[key]+': '+counts[key]+' cases');seg.onclick=()=>setBand(key);bar.append(seg)}
  document.querySelectorAll('.tab').forEach(t=>{const key=t.dataset.band;t.querySelector('span').textContent=key?counts[key]:total;if(['urgent','closed','outside_scope'].includes(key))t.hidden=!counts[key]&&selectedBand!==key;t.setAttribute('aria-pressed',String(key===selectedBand))});
  $('twReviewNext').disabled=!total;
}
async function assessNextTrialwatchCase(){
  const button=$('twReviewNext');button.disabled=true;
  try{const data=await api('/api/cases?sort=combined&limit=200');const next=data.items.find(c=>!c.case_review.score_eligible||!c.trialwatch_relevance.fit_review.score_eligible)||data.items[0];if(next)await detail(next.cnr)}catch(e){error(e)}finally{button.disabled=false}
}
function twField(key,facts){const [label,options,help]=TW_FIELDS[key],wrap=el('label',undefined,'tw-field');wrap.append(el('span',label));const select=el('select');select.id='tw-'+key;select.name=key;select.setAttribute('aria-label',label);for(const [value,text] of options){const opt=el('option',text);opt.value=value;select.append(opt)}select.value=facts[key];select.onchange=updateRelevanceForm;wrap.append(select,el('small',help));return wrap}

function renderRelevance(c){
  const r=c.trialwatch_relevance,facts=r.facts,p=c.case_priority,card=el('div',undefined,'unified-card'),head=el('div',undefined,'unified-head'),title=el('div'),score=el('div',undefined,'unified-score');
  title.append(el('span','REVIEW PRIORITY','eyebrow'),queueBadge(p));score.append(el('strong',p.score_display.replace('/100','')),el('small','/ 100'));head.append(title,score);card.append(head);
  const inputs=el('div',undefined,'score-inputs');
  for(const [label,value,range,hint] of [['Law concern',p.law_score_display,p.law_normalized_range,'Highest associated law'],['TrialWatch fit',p.fit_score_display,p.fit_score_range,r.assessment_source==='automatic'?'Document-based assessment':'Checked support needs']]){
    const row=el('div',undefined,'score-input'),name=el('div',undefined,'score-input-title');name.append(el('span',label),el('b',value));const track=el('div',undefined,'input-track'),fill=el('span');fill.style.width=(range?range[0]:0)+'%';track.append(fill);row.append(name,track,el('small',hint));inputs.append(row)
  }card.append(inputs);
  const priorityReason=p.urgent_override?'A verified urgent need takes precedence.':p.fit_rejected?'Marked outside TrialWatch fit. Retained for monitoring or referral.':p.band==='verify'?'Check the law scope or current facts before relying on this priority.':'Equal blend of law concern and opportunity to help.';
  card.append(el('p',priorityReason,'unified-reason'),renderAssessment(c));
  const a=r.automatic_assessment,assessment=el('details',undefined,'tw-assessment-evidence');assessment.append(el('summary','Score & supporting evidence'),el('p','50% law concern + 50% TrialWatch fit. Provisional review index; not a finding of misuse or a probability.'));
  if(r.has_assessment)assessment.append(el('p','Checked support needs: '+r.facts.evidence_note));
  const reasons=el('ul');for(const reason of a.reasons)reasons.append(el('li',reason));assessment.append(reasons);
  if(a.peer_feedback.yes+a.peer_feedback.no)assessment.append(el('p',`${a.peer_feedback.yes} Yes / ${a.peer_feedback.no} No checks from other same-law cases · ${a.peer_feedback.score_shift>=0?'+':''}${a.peer_feedback.score_shift} automatic fit points.`));
  for(const q of a.evidence){const passage=el('div',undefined,'tw-passage');passage.append(el('b',q.topic+' · '+date(q.order_date)+' · page '+q.page),el('blockquote',q.quote),linkButton('Read source order ↗',q.pdf_url,true));assessment.append(passage)}card.append(assessment);
  const editor=el('details',undefined,'tw-editor');editor.id='twEditor';editor.append(el('summary',r.has_assessment?'Edit checked support needs':'Add checked support needs · optional'));
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
  const actions=el('div',undefined,'review-actions'),save=el('button','Save checked needs','btn primary');save.id='twSave';save.type='submit';actions.append(save);form.append(actions);
  const message=el('div',undefined,'review-message');message.id='twMessage';message.setAttribute('role','status');message.setAttribute('aria-live','polite');form.append(message);editor.append(form);card.append(editor);
  /* Keep support needs optional; one compact primary review card. */
  card.append(el('p',r.has_assessment?'Last saved '+datetime(r.updated_at)+'. Unknown facts contribute a range. Source changes require recheck.':'Source changes trigger recheck. Reviews remain editable.','tw-foot'));
  $('trialwatchReview').replaceChildren(card);updateRelevanceForm();updateAssessment();
}

function updateRelevanceForm(){
  if(!$('twForm'))return;
  const scheduled=$('tw-deadline_status').value==='scheduled';$('twDateWrap').hidden=!scheduled;$('tw-next_deadline').required=scheduled;
  $('twOpenings').hidden=!['ready','to_arrange'].includes($('tw-opening_status').value);
  const closed=$('tw-workflow_status').value==='closed';$('twCloseWrap').hidden=!closed;$('tw-close_reason').required=closed;
  for(const input of $('twForm').querySelectorAll('input,select,textarea,button'))input.disabled=relevanceBusy;
  $('twSave').textContent=relevanceBusy?'Saving…':'Save checked needs';
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


function renderAssessment(c){
  const m=c.case_review,f=c.trialwatch_relevance.fit_review;
  assessmentDraft={misuse:m.decision,fit:f.decision};
  const section=el('section',undefined,'unified-assessment'),head=el('div',undefined,'assessment-caption');head.append(el('b','Your assessment'),el('small',m.needs_recheck||f.needs_recheck?'Evidence changed · recheck':m.decision||f.decision?'Saved review':'Two quick checks'));section.append(head);
  for(const [key,label,hint,options] of [['misuse','Law misuse?','Does the record support a misuse concern?',[['misuse','Yes'],['no_misuse','No']]],['fit','TrialWatch fit?','Is there a useful role for TrialWatch?',[['yes','Yes'],['no','No']]]]){
    const row=el('div',undefined,'assessment-question'),text=el('div');text.append(el('b',label),el('small',hint));const choices=el('div',undefined,'answer-choices');choices.setAttribute('role','group');choices.setAttribute('aria-label',label);
    for(const [value,title] of options){const button=el('button',title,'answer-choice');button.type='button';button.dataset.task=key;button.dataset.value=value;button.setAttribute('aria-label',label+' '+title);button.setAttribute('aria-pressed',String(assessmentDraft[key]===value));button.onclick=()=>{assessmentDraft[key]=value;updateAssessment()};choices.append(button)}row.append(text,choices);section.append(row)
  }
  const targets=el('div',undefined,'unified-targets');targets.id='assessmentTargets';targets.append(el('small','Apply misuse assessment to the law you verified:'));const options=el('div',undefined,'review-law-options');
  for(const profile of c.review_law_options){const label=el('label',undefined,'review-law-option'),input=el('input');input.type='checkbox';input.value=profile.id;input.name='reviewLaw';input.checked=m.decision?m.law_profile_ids.includes(profile.id):c.review_law_options.length===1;input.setAttribute('aria-label','Apply assessment to '+profile.profile_scope);input.onchange=updateAssessment;label.append(input,el('span',profile.profile_scope));options.append(label)}targets.append(options);if(!c.review_law_options.length)targets.append(el('small','No applicable scored profile. This saves a case label without changing a law score.'));section.append(targets);
  const label=el('label',undefined,'assessment-note');label.append(el('span','Reason or evidence · optional'));const note=el('textarea');note.id='assessmentNote';note.maxLength=1500;note.rows=2;note.placeholder='What in the record supports your review?';note.value=m.note||f.note||'';note.setAttribute('aria-label','Review reason or evidence');note.oninput=updateAssessment;label.append(note);section.append(label);
  const impact=el('div',undefined,'assessment-impact');impact.id='assessmentImpact';impact.setAttribute('aria-live','polite');section.append(impact);
  const actions=el('div',undefined,'assessment-actions'),clear=el('button','Clear review','btn quiet');clear.id='assessmentClear';clear.type='button';clear.hidden=!m.decision&&!f.decision;clear.onclick=()=>submitAssessment(true);const save=el('button','Save review','btn primary');save.id='assessmentSave';save.type='button';save.onclick=()=>submitAssessment(false);actions.append(clear,save);section.append(actions);const message=el('div',undefined,'review-message');message.id='assessmentMessage';message.setAttribute('role','status');message.setAttribute('aria-live','polite');section.append(message);return section;
}
function chosenLaws(){return [...document.querySelectorAll('input[name=reviewLaw]:checked')].map(n=>n.value).sort()}
function updateAssessment(){
  if(!currentCase||!$('assessmentSave'))return;
  const c=currentCase,m=c.case_review,f=c.trialwatch_relevance.fit_review;
  document.querySelectorAll('.answer-choice').forEach(b=>{b.setAttribute('aria-pressed',String(assessmentDraft[b.dataset.task]===b.dataset.value));b.disabled=assessmentBusy});
  $('assessmentTargets').hidden=!assessmentDraft.misuse;document.querySelectorAll('input[name=reviewLaw]').forEach(b=>b.disabled=assessmentBusy);$('assessmentNote').disabled=assessmentBusy;
  const laws=assessmentDraft.misuse?chosenLaws():[],note=$('assessmentNote').value.trim(),any=assessmentDraft.misuse||assessmentDraft.fit;
  const dirty=assessmentDraft.misuse!==m.decision||assessmentDraft.fit!==f.decision||JSON.stringify(laws)!==JSON.stringify([...m.law_profile_ids].sort())||note!==(m.note||f.note||'')||m.needs_recheck||f.needs_recheck;
  const needLaw=assessmentDraft.misuse&&c.review_law_options.length&&!laws.length,missing=!c.documents.some(d=>d.status==='ready');
  $('assessmentSave').disabled=assessmentBusy||!any||!dirty||Boolean(needLaw)||missing;$('assessmentSave').textContent=assessmentBusy?'Saving…':!dirty&&any?'Review saved':'Save review';$('assessmentClear').disabled=assessmentBusy;
  const impact=$('assessmentImpact');impact.replaceChildren();if(!dirty)return;if(missing){impact.textContent='Read an available document before saving.';return}if(needLaw){impact.textContent='Select the law you verified before saving.';return}
  if(assessmentDraft.misuse)for(const p of c.review_law_options){if(!laws.includes(p.id))continue;let yes=p.yes_reviews,no=p.no_reviews;if(m.score_eligible&&m.law_profile_ids.includes(p.id)){if(m.decision==='misuse')yes--;else no--}if(assessmentDraft.misuse==='misuse')yes++;else no++;const after=(6*p.original_score+12*yes)/(6+yes+no);impact.append(el('small',`${p.profile_scope}: ${p.adjusted_score.toFixed(1)} → ${after.toFixed(1)}/12`))}
  if(assessmentDraft.fit)impact.append(el('small',assessmentDraft.fit==='yes'?(c.trialwatch_relevance.assessment_source==='reviewer'?'Fit Yes confirms relevance; checked support needs retain their score.':'Fit Yes strengthens the recommendation.'):'Fit No lowers priority; verified urgent needs remain first.'));
}
async function submitAssessment(clear){
  if(assessmentBusy||!currentCase)return;
  const c=currentCase,cnr=c.cnr,body={expected_misuse_revision:c.case_review.revision,expected_fit_revision:c.trialwatch_relevance.fit_review.revision};
  if(!clear)Object.assign(body,{misuse_decision:assessmentDraft.misuse,fit_decision:assessmentDraft.fit,law_profile_ids:assessmentDraft.misuse?chosenLaws():[],note:$('assessmentNote').value.trim(),evidence_version:c.review_evidence_version});
  assessmentBusy=true;updateAssessment();$('assessmentMessage').textContent='';
  try{const updated=await api('/api/cases/'+encodeURIComponent(cnr)+'/assessment',{method:clear?'DELETE':'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assessmentBusy=false;if(currentCase?.cnr===cnr&&$('detail').open){renderCase(updated);$('assessmentMessage').textContent=clear?'Review cleared. Its contributions have been removed.':'Review saved. Scores and queue updated.'}await Promise.all([status(),list(),globalSummary()]);}
  catch(e){assessmentBusy=false;if(currentCase?.cnr===cnr){updateAssessment();const message=$('assessmentMessage');message.classList.add('error');message.textContent=e.message;if(e.status===409){const reload=el('button','Reload current case','review-reload');reload.onclick=()=>detail(cnr);message.append(reload)}}}
}
