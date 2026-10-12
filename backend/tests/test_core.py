import pytest
from io import BytesIO
from backend.app.parsing import extract_file,chunk_pages
from backend.app.evaluation import reciprocal_rank
from backend.app.providers import LocalProvider
from unittest.mock import patch

def test_txt_parsing_and_chunking():
 parts=extract_file('notes.txt','text/plain',b'hello world ' * 200)
 chunks=chunk_pages(parts,size=100,overlap=20)
 assert len(chunks)>2 and chunks[0][0] is None

def test_rejects_empty_and_invalid_files():
 with pytest.raises(ValueError,match='no readable'):
  extract_file('blank.txt','text/plain',b'  ')
 with pytest.raises(ValueError,match='Only PDF'):
  extract_file('file.exe','application/octet-stream',b'no')

def test_deterministic_embeddings_are_normalized():
 a=LocalProvider().embed(['annual leave'])[0]
 assert len(a)==1536 and abs(sum(x*x for x in a)-1)<0.0001

def test_mrr_calculation():
 assert reciprocal_rank([4,7,3],{7})==0.5
 assert reciprocal_rank([4],{7})==0

def test_docx_image_ocr_is_included():
 pytest.importorskip('PIL')
 from docx import Document
 from docx.shared import Inches
 from PIL import Image
 image=BytesIO();Image.new('RGB',(10,10),'white').save(image,format='PNG')
 doc=Document();doc.add_picture(BytesIO(image.getvalue()),width=Inches(1));out=BytesIO();doc.save(out)
 with patch('backend.app.parsing.ocr_image',return_value='Amount Rs 17742.00'):
  parts=extract_file('slip.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document',out.getvalue())
 assert '17742.00' in parts[0][1]
