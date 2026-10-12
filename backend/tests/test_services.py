from unittest.mock import patch
from backend.app.services import answer,citation
from backend.app.providers import LocalProvider

class FakeDB: pass
def test_citation_preserves_document_and_location():
 c={'_id':'2','ordinal':3,'page':4,'text':'evidence','document_name':'policy.pdf'}
 out=citation(c)
 assert out.document_name=='policy.pdf' and out.page==4 and out.chunk_ordinal==3
def test_insufficient_evidence_has_no_citations():
 with patch('backend.app.services.retrieve',return_value=[]),patch('backend.app.services.provider',return_value=LocalProvider()):
  text,cites,ok=answer(FakeDB(),'unrelated question','semantic',4,False)
 assert not ok and not cites and 'enough evidence' in text
