import math,re
from .schemas import Citation
from .providers import provider,LocalProvider
def cosine(a,b): return sum(x*y for x,y in zip(a,b))/(math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b)) or 1)
STOP_WORDS={'a','an','and','are','as','at','be','by','file','for','from','how','i','in','is','it','of','on','or','the','this','to','what','when','where','which','who','why','with'}
def keywords(text):return {word for word in re.findall(r"[a-z0-9]+",text.lower()) if word not in STOP_WORDS and len(word)>1}
def retrieve(db,question,strategy,k,rerank=False,embedder=None,workspace_id=None,document_ids=None):
 qvec=(embedder or provider()).embed([question])[0];terms=keywords(question);query={}
 if workspace_id: query['workspace_id']=workspace_id
 if document_ids: query['document_id']={'$in':document_ids}
 chunks=list(db.chunks.find(query) if query else db.chunks.find())
 for c in chunks:
  c['_semantic']=cosine(qvec,c.get('embedding',[]));c['_keyword']=len(terms & keywords(c['text']));c['_name_match']=len(terms & keywords(c['document_name']))
 chunks.sort(key=lambda c:(c['_semantic']+.1*c['_keyword']) if strategy=='hybrid' else c['_semantic'],reverse=True)
 # If a meaningful query word occurs in a document, prefer that document's chunks
 # over merely similar chunks from unrelated uploads.
 # An explicit filename/reference in the question is the strongest retrieval signal.
 best_name_match=max((c['_name_match'] for c in chunks),default=0)
 if best_name_match: chunks=[c for c in chunks if c['_name_match']==best_name_match]
 else:
  matched_documents={c['document_id'] for c in chunks if c['_keyword']>0}
  if matched_documents:chunks=[c for c in chunks if c['document_id'] in matched_documents]
 if rerank:chunks[:k*3]=sorted(chunks[:k*3],key=lambda c:c['_keyword'],reverse=True)
 return chunks[:k]
def retrieve_resilient(db,question,strategy,k,rerank=False,workspace_id=None,document_ids=None):
 try:
  active=provider();return retrieve(db,question,strategy,k,rerank,active,workspace_id,document_ids)
 except Exception:return retrieve(db,question,strategy,k,rerank,LocalProvider(),workspace_id,document_ids)
def citation(c):return Citation(chunk_id=str(c['_id']),document_name=c['document_name'],page=c.get('page'),chunk_ordinal=c['ordinal'],excerpt=c['text'][:240])
def answer(db,question,strategy,k,rerank,workspace_id=None,document_ids=None):
 try:
  active=provider();chunks=retrieve(db,question,strategy,k,rerank,active,workspace_id,document_ids)
 except Exception:
  # Preserve document search during a transient Gemini/network outage.
  active=LocalProvider();chunks=retrieve(db,question,strategy,k,rerank,active,workspace_id,document_ids)
 try: text,ok=active.answer(question,chunks)
 except Exception: text,ok=LocalProvider().answer(question,chunks)
 # Avoid repeating identical chunks when the same file was uploaded more than once.
 unique=[];seen=set()
 for chunk in chunks:
  key=(chunk['document_name'],chunk['text'])
  if key not in seen:unique.append(chunk);seen.add(key)
 if {'salary','amount'} & keywords(question):
  monetary=[c for c in unique if re.search(r'\b\d{3,}(?:\.\d{2})\b',c['text'])]
  if monetary: unique=monetary[:1]
 return text,[citation(c) for c in unique] if ok else [],ok
