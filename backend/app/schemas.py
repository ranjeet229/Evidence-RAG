from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
class Citation(BaseModel):
    chunk_id:str; document_name:str; page:int|None=None; chunk_ordinal:int; excerpt:str
class AskRequest(BaseModel):
    question:str = Field(min_length=2, max_length=2000)
    strategy:Literal['semantic','hybrid']='semantic'
    rerank:bool=False
    k:int=Field(default=4, ge=1, le=20)
class AskResponse(BaseModel): answer:str; citations:list[Citation]; sufficient_evidence:bool; strategy:str
class DocumentOut(BaseModel): id:str; name:str; chunk_count:int; created_at:datetime
class EvalRequest(BaseModel): strategy:Literal['semantic','hybrid']='semantic'; rerank:bool=False; k:int=Field(4,ge=1,le=20); use_ragas:bool=False
class EvalOut(BaseModel): id:str; created_at:datetime; strategy:str; settings:dict; results:dict
