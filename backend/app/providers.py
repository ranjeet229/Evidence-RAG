import hashlib, math,re
from .config import settings
class LocalProvider:
    def embed(self, texts):
        vectors=[]
        for text in texts:
            v=[0.0]*1536
            for token in text.lower().split(): v[int(hashlib.sha256(token.encode()).hexdigest(),16)%1536]+=1
            norm=math.sqrt(sum(x*x for x in v)) or 1; vectors.append([x/norm for x in v])
        return vectors
    def answer(self, question, contexts):
        if not contexts: return 'I do not have enough evidence in the uploaded documents to answer that.', False
        q=set(question.lower().split()); ranked=sorted(contexts,key=lambda c:len(q & set(c['text'].lower().split())),reverse=True)
        if {'salary','amount'} & q:
            monetary=[c for c in contexts if re.search(r'\b\d{3,}(?:\.\d{2})\b',c['text'])]
            if monetary:
                value=re.search(r'\b\d{3,}(?:\.\d{2})\b',monetary[0]['text']).group(0)
                return f'The salary amount mentioned is ₹{float(value.replace(",", "")):,.2f}.',True
        if not (q & set(ranked[0]['text'].lower().split())): return 'I do not have enough evidence in the uploaded documents to answer that.', False
        return ranked[0]['text'][:600], True
class GeminiProvider:
    def __init__(self):
        from google import genai
        self.client=genai.Client(api_key=settings.gemini_api_key)
    def embed(self,texts):
        return [x.values for x in self.client.models.embed_content(model='gemini-embedding-001',contents=texts).embeddings]
    def answer(self,question,contexts):
        if not contexts:return 'I do not have enough evidence in the uploaded documents to answer that.',False
        excerpts='\n\n'.join(f"[{i+1}] {c['text']}" for i,c in enumerate(contexts))
        prompt=f'''Answer only from the supplied excerpts. If they do not support an answer, say exactly: I do not have enough evidence in the uploaded documents to answer that.\n\nQuestion: {question}\n\nExcerpts:\n{excerpts}'''
        text=self.client.models.generate_content(model=settings.gemini_model,contents=prompt,config={'temperature':0}).text or ''
        return text, 'enough evidence' not in text.lower()
def provider():
    if settings.model_provider=='gemini': return GeminiProvider()
    return LocalProvider()
