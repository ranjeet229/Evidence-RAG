from datetime import datetime,timezone
from .database import get_db
from .providers import provider
from .parsing import chunk_pages
SEEDS={'leave-policy.txt':'Employees receive 20 days of annual leave each calendar year. Leave requests should be approved by a manager before travel is booked.','expenses.txt':'Business expenses must be submitted within 30 days of purchase. Receipts are required for expenses over $25.'}
def main():
 dependency=get_db();db=next(dependency)
 try:
  if db.documents.count_documents({}):return
  for name,text in SEEDS.items():
   pieces=chunk_pages([(None,text)]);doc={'name':name,'content_type':'text/plain','created_at':datetime.now(timezone.utc),'chunk_count':len(pieces)};doc['_id']=db.documents.insert_one(doc).inserted_id
   for i,((page,chunk),vec) in enumerate(zip(pieces,provider().embed([x[1] for x in pieces])),1):db.chunks.insert_one({'document_id':str(doc['_id']),'document_name':name,'ordinal':i,'page':page,'text':chunk,'embedding':vec})
 finally:
  dependency.close()
if __name__=='__main__':main()
