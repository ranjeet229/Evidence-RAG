from unittest.mock import patch
from backend.app.services import answer
from backend.app.providers import LocalProvider
def test_answer_falls_back_when_primary_embedding_fails():
 chunk={'_id':'1','document_id':'d1','document_name':'salary.docx','ordinal':1,'text':'Salary amount is 17742.00','embedding':[0.0]*1536}
 class Collection:
  def find(self):return [chunk]
 class DB: chunks=Collection()
 with patch('backend.app.services.provider',side_effect=RuntimeError('network')):
  text,citations,ok=answer(DB(),'what is the salary amount','semantic',4,False)
 assert ok and '17,742.00' in text and citations[0].document_name=='salary.docx'
