# Evidence RAG

A document question-answering application with source citations and a repeatable RAG benchmark.

## Requirements

Python 3.11+, Node 20+, and a MongoDB Atlas database. No Docker is required.

For scanned PDFs or DOCX files containing screenshots, install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) and ensure `tesseract` is available on your PATH. The app uses local OCR; uploaded content is not sent to an OCR service.

## Quick start

```powershell
# Update GEMINI_API_KEY in .env (MONGO_URI is already configured)
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m backend.app.seed
uvicorn backend.app.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). The API docs are at `http://localhost:8000/docs`.

## Models

Set `GEMINI_API_KEY` and configure `GEMINI_MODEL` in `.env` to use Gemini. The default model is `gemini-3.5-flash-lite`; confirm its availability for your Gemini account. Model calls are isolated behind `app.providers`.

## Evaluation

Seed data installs two short policy documents and benchmark questions. On the Evaluation page choose a strategy and k, then run it. Retrieval metrics (Recall@k, MRR) are calculated locally. Faithfulness and answer relevance are only shown when a configured evaluator returns them; otherwise their values are `not evaluated`—never invented. Runs and full settings are persisted.

## Checks

```powershell
pytest backend/tests -q
cd frontend; npm run check; npm run build
```

## Main architecture

`documents`, `chunks`, and evaluation runs are stored in MongoDB. Upload processing extracts text, chunks it with page/location metadata, and embeds it. The retrieval service supports semantic, hybrid (keyword + vector), and a deterministic optional lexical reranker. Answers are constrained to the retrieved excerpts and citations are constructed from those same chunks.
