"""Attach pre-V2 documents to an existing account's workspace.

Run once after creating your first account:
    python -m backend.app.migrate_legacy you@example.com
"""
import sys
from .database import get_db

def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m backend.app.migrate_legacy you@example.com')
    generator = get_db(); db = next(generator)
    try:
        user = db.users.find_one({'email': sys.argv[1].strip().lower()})
        if not user: raise SystemExit('No account found for that email. Create it in the app first.')
        workspace_id = user['workspace_id']
        documents = list(db.documents.find({'workspace_id': {'$exists': False}}))
        document_ids = [str(document['_id']) for document in documents]
        if documents:
            db.documents.update_many({'_id': {'$in': [document['_id'] for document in documents]}}, {'$set': {'workspace_id': workspace_id}})
            db.chunks.update_many({'document_id': {'$in': document_ids}, 'workspace_id': {'$exists': False}}, {'$set': {'workspace_id': workspace_id}})
        print(f'Moved {len(documents)} legacy document(s) into {user["email"]}\'s workspace.')
    finally:
        generator.close()

if __name__ == '__main__': main()
