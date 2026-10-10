"""Atomic, one-button review for independent misuse and fit labels."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .feedback import ReviewError, write_review, contexts
from .trialwatch_fit import FitInput, save as save_fit


class AssessmentInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    misuse_decision:Literal['misuse','no_misuse']|None=None
    fit_decision:Literal['yes','no']|None=None
    law_profile_ids:list[str]=Field(default_factory=list,max_length=7)
    note:str=Field('',max_length=1500)
    expected_misuse_revision:int=Field(0,ge=0)
    expected_fit_revision:int=Field(0,ge=0)
    evidence_version:str=Field(pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def some_label(self):
        if not self.misuse_decision and not self.fit_decision:
            raise ValueError('Answer at least one review question before saving.')
        if self.law_profile_ids and not self.misuse_decision:
            raise ValueError('A law selection needs a misuse assessment.')
        return self


class ClearAssessment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_misuse_revision:int=Field(ge=0)
    expected_fit_revision:int=Field(ge=0)


def save(store,cnr,data,*,clear=False):
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        context=contexts(db).get(cnr)
        if not context:
            raise ReviewError(404,'Case not found')
        for table,expected in [('case_reviews',data.expected_misuse_revision),('case_fit_reviews',data.expected_fit_revision)]:
            row=db.execute('SELECT revision FROM '+table+' WHERE cnr=?',(cnr,)).fetchone()
            if expected != (row['revision'] if row else 0):
                raise ReviewError(409,'This review changed in another window. Reload before saving.')
        if not clear and data.evidence_version != context['evidence_version']:
            raise ReviewError(409,'Case evidence changed. Reload before saving.')
        if clear or data.misuse_decision:
            write_review(store,cnr,{'decision':None if clear else data.misuse_decision,
                                   'law_profile_ids':[] if clear else data.law_profile_ids,
                                   'note':'' if clear else data.note,
                                   'expected_revision':data.expected_misuse_revision,
                                   'evidence_version':context['evidence_version']},clear=clear,connection=db)
        if clear or data.fit_decision:
            fit=FitInput(decision='yes' if clear else data.fit_decision,
                         note='' if clear else data.note,expected_revision=data.expected_fit_revision,
                         evidence_version=context['evidence_version'])
            save_fit(store,cnr,fit,clear=clear,connection=db)
