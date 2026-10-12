from datetime import datetime,timezone
from fastapi import FastAPI,UploadFile,File,Depends,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import get_db
from .schemas import *
from .config import settings
from .parsing import extract_file,chunk_pages
from .providers import provider,LocalProvider
from .services import answer
from .evaluation import run_evaluation
from bson import ObjectId
from bson import ObjectId
app=FastAPI(title='Evidence RAG API');app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(','),allow_methods=['*'],allow_headers=['*'])
def as_utc(value):return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
@app.get('/health')
def health():return {'ok':True}
@app.get('/documents',response_model=list[DocumentOut])
def documents(db=Depends(get_db)):
 return [DocumentOut(id=str(d['_id']),name=d['name'],chunk_count=count,created_at=d['created_at']) for d in db.documents.find() if (count:=db.chunks.count_documents({'document_id':str(d['_id'])}))]
@app.post('/documents',response_model=DocumentOut)
async def upload(file:UploadFile=File(...),db=Depends(get_db)):
 data=await file.read()
 if len(data)>settings.max_upload_mb*1024*1024:raise HTTPException(413,'File exceeds upload size limit.')
 try:parts=extract_file(file.filename or '',file.content_type,data)
 except ValueError as e:raise HTTPException(400,str(e))
 pieces=chunk_pages(parts)
 try: vectors=provider().embed([x[1] for x in pieces])
 except Exception: vectors=LocalProvider().embed([x[1] for x in pieces])
 # A re-upload replaces prior copies with the same visible filename, preventing
 # duplicate documents and citations while preserving atomic indexing above.
 for old in db.documents.find({'name':file.filename or 'upload'}):
  db.chunks.delete_many({'document_id':str(old['_id'])})
 db.documents.delete_many({'name':file.filename or 'upload'})
 doc={'name':file.filename or 'upload','content_type':file.content_type or '','created_at':datetime.now(timezone.utc),'chunk_count':len(pieces)};doc['_id']=db.documents.insert_one(doc).inserted_id
 for i,((page,text),vec) in enumerate(zip(pieces,vectors),1):db.chunks.insert_one({'document_id':str(doc['_id']),'document_name':doc['name'],'ordinal':i,'page':page,'text':text,'embedding':vec})
 return DocumentOut(id=str(doc['_id']),name=doc['name'],chunk_count=len(pieces),created_at=doc['created_at'])
@app.delete('/documents/{document_id}',status_code=204)
def delete_document(document_id:str,db=Depends(get_db)):
 try: document=db.documents.find_one({'_id':ObjectId(document_id)})
 except Exception: raise HTTPException(404,'Document not found.')
 if not document: raise HTTPException(404,'Document not found.')
 old=list(db.documents.find({'name':document['name']}))
 db.chunks.delete_many({'document_id':{'$in':[str(item['_id']) for item in old]}})
 db.documents.delete_many({'_id':{'$in':[item['_id'] for item in old]}})
@app.delete('/documents/{document_id}',status_code=204)
def delete_document(document_id:str,db=Depends(get_db)):
 try: document=db.documents.find_one({'_id':ObjectId(document_id)})
 except Exception: raise HTTPException(404,'Document not found.')
 if not document: raise HTTPException(404,'Document not found.')
 # Delete same-name duplicates created by earlier re-uploads as one library item.
 old=list(db.documents.find({'name':document['name']}))
 db.chunks.delete_many({'document_id':{'$in':[str(item['_id']) for item in old]}})
 db.documents.delete_many({'_id':{'$in':[item['_id'] for item in old]}})
@app.post('/chat',response_model=AskResponse)
def chat(req:AskRequest,db=Depends(get_db)):
 try:
  text,citations,ok=answer(db,req.question,req.strategy,req.k,req.rerank)
  return AskResponse(answer=text,citations=citations,sufficient_evidence=ok,strategy=req.strategy)
 except Exception as exc:
  # Do not expose provider internals or secrets in browser responses/logs.
  raise HTTPException(503,'The Gemini service could not be reached. Check network access, API key, and model availability, then try again.') from exc
@app.post('/evaluations',response_model=EvalOut)
def evaluate(req:EvalRequest,db=Depends(get_db)):
 r=run_evaluation(db,req.strategy,req.k,req.rerank,req.use_ragas);return EvalOut(id=str(r['_id']),created_at=r['created_at'],strategy=r['strategy'],settings=r['settings'],results=r['results'])
@app.get('/evaluations',response_model=list[EvalOut])
def evaluations(db=Depends(get_db)):return [EvalOut(id=str(r['_id']),created_at=as_utc(r['created_at']),strategy=r['strategy'],settings=r['settings'],results=r['results']) for r in db.evaluation_runs.find().sort('created_at',-1)]
