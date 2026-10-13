from datetime import datetime,timezone
from .services import retrieve_resilient,answer
BENCHMARK=[{'question':'How many annual leave days are available?','source_text':'Employees receive 20 days'},{'question':'When must expenses be submitted?','source_text':'submitted within 30 days'}]
def reciprocal_rank(ids,relevant):
 for i,x in enumerate(ids,1):
  if x in relevant:return 1/i
 return 0
def run_evaluation(db,strategy,k,rerank,use_ragas,workspace_id=None):
 recalls=[];mrr=[]
 for case in BENCHMARK:
  query={'text':{'$regex':case['source_text']}}
  if workspace_id: query['workspace_id']=workspace_id
  relevant={str(c['_id']) for c in db.chunks.find(query)};found=retrieve_resilient(db,case['question'],strategy,k,rerank,workspace_id);ids=[str(c['_id']) for c in found]
  recalls.append(float(bool(relevant&set(ids))));mrr.append(reciprocal_rank(ids,relevant))
 results={'questions':len(BENCHMARK),'recall_at_k':sum(recalls)/len(recalls),'mrr':sum(mrr)/len(mrr),'faithfulness':None,'answer_relevance':None,'ragas_status':'not evaluated: configure an external RAGAS evaluator' if use_ragas else 'not requested'}
 run={'created_at':datetime.now(timezone.utc),'strategy':strategy,'settings':{'k':k,'rerank':rerank,'use_ragas':use_ragas},'results':results}
 if workspace_id:run['workspace_id']=workspace_id
 run['_id']=db.evaluation_runs.insert_one(run).inserted_id;return run
