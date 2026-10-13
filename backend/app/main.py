from datetime import datetime, timezone
import re
from bson import ObjectId
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import DuplicateKeyError
from .auth import create_token, current_user, hash_password, verify_password
from .config import settings
from .database import get_db
from .evaluation import run_evaluation
from .parsing import chunk_pages, extract_file
from .providers import LocalProvider, provider
from .schemas import *
from .services import answer

app = FastAPI(title='Evidence RAG API')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(','), allow_methods=['*'], allow_headers=['*'])

def user_out(user): return UserOut(id=str(user['_id']), name=user['name'], email=user['email'], workspace_id=user['workspace_id'], role=user['role'])

@app.on_event('startup')
def indexes():
    from pymongo import ASCENDING, DESCENDING
    generator = get_db(); db = next(generator)
    try:
        db.users.create_index([('email', ASCENDING)], unique=True)
        db.documents.create_index([('workspace_id', ASCENDING), ('created_at', DESCENDING)])
        db.chunks.create_index([('workspace_id', ASCENDING), ('document_id', ASCENDING)])
        db.evaluation_runs.create_index([('workspace_id', ASCENDING), ('created_at', DESCENDING)])
    finally: generator.close()

@app.get('/health')
def health(): return {'ok': True, 'service': 'evidence-rag'}

@app.post('/auth/signup', response_model=AuthOut, status_code=201)
def signup(req: SignUpRequest, db=Depends(get_db)):
    email = req.email.strip().lower()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email): raise HTTPException(422, 'Enter a valid email address.')
    now = datetime.now(timezone.utc); workspace = {'name': f"{req.name.strip()}'s workspace", 'created_at': now}
    workspace['_id'] = db.workspaces.insert_one(workspace).inserted_id
    user = {'name': req.name.strip(), 'email': email, 'password_hash': hash_password(req.password), 'workspace_id': str(workspace['_id']), 'role': 'owner', 'created_at': now}
    try: user['_id'] = db.users.insert_one(user).inserted_id
    except DuplicateKeyError:
        db.workspaces.delete_one({'_id': workspace['_id']}); raise HTTPException(409, 'An account with this email already exists.')
    return AuthOut(token=create_token(str(user['_id']), user['workspace_id']), user=user_out(user))

@app.post('/auth/signin', response_model=AuthOut)
def signin(req: SignInRequest, db=Depends(get_db)):
    user = db.users.find_one({'email': req.email.strip().lower()})
    if not user or not verify_password(req.password, user.get('password_hash', '')): raise HTTPException(401, 'Incorrect email or password.')
    return AuthOut(token=create_token(str(user['_id']), user['workspace_id']), user=user_out(user))

@app.get('/auth/me', response_model=UserOut)
def me(user=Depends(current_user)): return user_out(user)

@app.patch('/auth/profile', response_model=UserOut)
def update_profile(req: ProfileUpdateRequest, user=Depends(current_user), db=Depends(get_db)):
    email = req.email.strip().lower(); name = req.name.strip()
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email): raise HTTPException(422, 'Enter a valid email address.')
    try:
        db.users.update_one({'_id': user['_id']}, {'$set': {'name': name, 'email': email}})
    except DuplicateKeyError: raise HTTPException(409, 'That email address is already in use.')
    return user_out({**user, 'name': name, 'email': email})

@app.post('/auth/password', status_code=204)
def change_password(req: PasswordChangeRequest, user=Depends(current_user), db=Depends(get_db)):
    if not verify_password(req.current_password, user.get('password_hash', '')): raise HTTPException(400, 'Your current password is incorrect.')
    db.users.update_one({'_id': user['_id']}, {'$set': {'password_hash': hash_password(req.new_password)}})

@app.get('/documents', response_model=list[DocumentOut])
def documents(user=Depends(current_user), db=Depends(get_db)):
    return [DocumentOut(id=str(d['_id']), name=d['name'], chunk_count=d.get('chunk_count', 0), created_at=d['created_at']) for d in db.documents.find({'workspace_id': user['workspace_id']}).sort('created_at', -1)]

@app.post('/documents', response_model=DocumentOut)
async def upload(file: UploadFile = File(...), user=Depends(current_user), db=Depends(get_db)):
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, 'File exceeds upload size limit.')
    try: pieces = chunk_pages(extract_file(file.filename or '', file.content_type, data))
    except ValueError as exc: raise HTTPException(400, str(exc)) from exc
    try: vectors = provider().embed([text for _, text in pieces])
    except Exception: vectors = LocalProvider().embed([text for _, text in pieces])
    name = file.filename or 'upload'; scope = {'workspace_id': user['workspace_id'], 'name': name}
    old_ids = [str(d['_id']) for d in db.documents.find(scope)]
    if old_ids: db.chunks.delete_many({'workspace_id': user['workspace_id'], 'document_id': {'$in': old_ids}})
    db.documents.delete_many(scope)
    doc = {'name': name, 'content_type': file.content_type or '', 'created_at': datetime.now(timezone.utc), 'chunk_count': len(pieces), 'workspace_id': user['workspace_id'], 'uploaded_by': str(user['_id'])}
    doc['_id'] = db.documents.insert_one(doc).inserted_id
    db.chunks.insert_many([{'workspace_id': user['workspace_id'], 'document_id': str(doc['_id']), 'document_name': name, 'ordinal': ordinal, 'page': page, 'text': text, 'embedding': vector} for ordinal, ((page, text), vector) in enumerate(zip(pieces, vectors), 1)])
    return DocumentOut(id=str(doc['_id']), name=name, chunk_count=len(pieces), created_at=doc['created_at'])

@app.delete('/documents/{document_id}', status_code=204)
def delete_document(document_id: str, user=Depends(current_user), db=Depends(get_db)):
    try: doc = db.documents.find_one({'_id': ObjectId(document_id), 'workspace_id': user['workspace_id']})
    except Exception: doc = None
    if not doc: raise HTTPException(404, 'Document not found.')
    db.chunks.delete_many({'workspace_id': user['workspace_id'], 'document_id': document_id}); db.documents.delete_one({'_id': doc['_id']})

@app.post('/chat', response_model=AskResponse)
def chat(req: AskRequest, user=Depends(current_user), db=Depends(get_db)):
    selected = list(req.document_ids)
    valid_ids = [ObjectId(x) for x in selected if ObjectId.is_valid(x)]
    if selected and (len(valid_ids) != len(selected) or db.documents.count_documents({'workspace_id': user['workspace_id'], '_id': {'$in': valid_ids}}) != len(selected)): raise HTTPException(400, 'One or more selected documents are unavailable.')
    try:
        text, citations, ok = answer(db, req.question, req.strategy, req.k, req.rerank, user['workspace_id'], selected or None)
        db.chat_history.insert_one({'workspace_id': user['workspace_id'], 'user_id': str(user['_id']), 'question': req.question, 'answer': text, 'strategy': req.strategy, 'document_ids': selected, 'created_at': datetime.now(timezone.utc)})
        return AskResponse(answer=text, citations=citations, sufficient_evidence=ok, strategy=req.strategy)
    except HTTPException: raise
    except Exception as exc: raise HTTPException(503, 'The answer service is temporarily unavailable. Please try again.') from exc

@app.post('/feedback', status_code=201)
def feedback(req: FeedbackRequest, user=Depends(current_user), db=Depends(get_db)):
    db.feedback.insert_one({'workspace_id': user['workspace_id'], 'user_id': str(user['_id']), **req.model_dump(), 'created_at': datetime.now(timezone.utc)}); return {'ok': True}

@app.post('/evaluations', response_model=EvalOut)
def evaluate(req: EvalRequest, user=Depends(current_user), db=Depends(get_db)):
    r = run_evaluation(db, req.strategy, req.k, req.rerank, req.use_ragas, user['workspace_id']); return EvalOut(id=str(r['_id']), created_at=r['created_at'], strategy=r['strategy'], settings=r['settings'], results=r['results'])

@app.get('/evaluations', response_model=list[EvalOut])
def evaluations(user=Depends(current_user), db=Depends(get_db)):
    return [EvalOut(id=str(r['_id']), created_at=r['created_at'], strategy=r['strategy'], settings=r['settings'], results=r['results']) for r in db.evaluation_runs.find({'workspace_id': user['workspace_id']}).sort('created_at', -1)]
