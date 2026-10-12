from io import BytesIO
from pathlib import Path
import shutil
from pypdf import PdfReader
from docx import Document as DocxDocument

SUPPORTED={'.pdf','application/pdf','.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document','.txt','text/plain'}
def ocr_image(data:bytes)->str:
    """Extract text from an image using local Tesseract; never send uploads elsewhere."""
    if not shutil.which('tesseract'):
        raise ValueError('This scanned document needs OCR. Install Tesseract OCR, then try again.')
    try:
        from PIL import Image
        import pytesseract
        return pytesseract.image_to_string(Image.open(BytesIO(data)))
    except Exception as e:
        raise ValueError('OCR could not read an embedded image.') from e
def ocr_pdf(data:bytes)->list[tuple[int,str]]:
    try:
        import fitz
        pdf=fitz.open(stream=data,filetype='pdf')
        return [(i+1,ocr_image(page.get_pixmap(matrix=fitz.Matrix(2,2)).tobytes('png'))) for i,page in enumerate(pdf)]
    except ValueError: raise
    except Exception as e: raise ValueError('OCR could not read this PDF.') from e
def extract_file(filename:str, content_type:str|None, data:bytes)->list[tuple[int|None,str]]:
    ext=Path(filename).suffix.lower()
    if ext not in {'.pdf','.docx','.txt'} or (content_type and content_type not in SUPPORTED): raise ValueError('Only PDF, DOCX, and TXT files are supported.')
    try:
        if ext=='.pdf':
            parts=[(i+1,p.extract_text() or '') for i,p in enumerate(PdfReader(BytesIO(data)).pages)]
            if not any(t.strip() for _,t in parts): parts=ocr_pdf(data)
        elif ext=='.docx':
            document=DocxDocument(BytesIO(data)); text='\n'.join(p.text for p in document.paragraphs)
            image_text='\n'.join(ocr_image(rel.target_part.blob) for rel in document.part.rels.values() if 'image' in rel.reltype)
            parts=[(None,'\n'.join(x for x in (text,image_text) if x.strip()))]
        else: parts=[(None,data.decode('utf-8'))]
    except Exception as e: raise ValueError('The file could not be read.') from e
    if not any(t.strip() for _,t in parts): raise ValueError('The document contains no readable text.')
    return parts
def chunk_pages(parts:list[tuple[int|None,str]], size:int=800, overlap:int=120):
    output=[]
    for page,text in parts:
        text=' '.join(text.split())
        start=0
        while start < len(text):
            end=min(len(text), start+size); output.append((page,text[start:end]))
            if end==len(text): break
            start=end-overlap
    return output
