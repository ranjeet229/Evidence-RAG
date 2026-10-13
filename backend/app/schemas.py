from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal
class SignUpRequest(BaseModel):
    name:str=Field(min_length=2,max_length=80)
    email:str=Field(min_length=5,max_length=254)
    password:str=Field(min_length=8,max_length=128)
class SignInRequest(BaseModel):
    email:str
    password:str
class UserOut(BaseModel):
    id:str; name:str; email:str; workspace_id:str; role:str
class AuthOut(BaseModel):
    token:str; user:UserOut
class ProfileUpdateRequest(BaseModel):
    name:str=Field(min_length=2,max_length=80)
    email:str=Field(min_length=5,max_length=254)
class PasswordChangeRequest(BaseModel):
    current_password:str=Field(min_length=1,max_length=128)
    new_password:str=Field(min_length=8,max_length=128)
class Citation(BaseModel):
    chunk_id:str; document_name:str; page:int|None=None; chunk_ordinal:int; excerpt:str
class AskRequest(BaseModel):
    question:str = Field(min_length=2, max_length=2000)
    strategy:Literal['semantic','hybrid']='semantic'
    rerank:bool=False
    k:int=Field(default=4, ge=1, le=20)
    document_ids:list[str]=Field(default_factory=list, max_length=50)
class AskResponse(BaseModel): answer:str; citations:list[Citation]; sufficient_evidence:bool; strategy:str
class DocumentOut(BaseModel): id:str; name:str; chunk_count:int; created_at:datetime
class FeedbackRequest(BaseModel):
    question:str=Field(min_length=2,max_length=2000)
    answer:str=Field(min_length=1,max_length=10000)
    rating:Literal['up','down']
    note:str=Field(default='',max_length=2000)
class EvalRequest(BaseModel): strategy:Literal['semantic','hybrid']='semantic'; rerank:bool=False; k:int=Field(4,ge=1,le=20); use_ragas:bool=False
class EvalOut(BaseModel): id:str; created_at:datetime; strategy:str; settings:dict; results:dict
