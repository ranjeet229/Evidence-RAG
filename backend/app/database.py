def get_db():
    from pymongo import MongoClient
    from .config import settings
    if not settings.mongo_uri: raise RuntimeError('MONGO_URI must be configured.')
    client=MongoClient(settings.mongo_uri)
    try: yield client[settings.mongo_database]
    finally: client.close()
