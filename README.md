# Gates Foundation AI Fellowship India 2026 — Technical Assignment

**Author:** Shlok Rana  
**Option:** A — Evaluate & Report  
**Live findings:** https://\<USERNAME\>.github.io/fellowship-assignment/

> Replace `<USERNAME>` with your GitHub username after enabling Pages on the `main` branch (`/findings` folder as the source root).

---

## What this is

Option A (Evaluate & Report) submission. A basic RAG FAQ chatbot grounded in two Gates Foundation program documents was built and then evaluated end-to-end with the [CeRAI AI Evaluation Tool](https://github.com/cerai-iitm/AIEvaluationTool). The findings document linked above is the primary deliverable; this repo contains the full source to reproduce both the chatbot and the evaluation.

## Path chosen

Option A was chosen because it creates a complete audit trail: the same artefacts that demonstrate the chatbot's capabilities also expose its failure modes in a measurable, reproducible way. Building a system and evaluating it with an independent tool forces honest accounting of limitations that a pure "build" submission can gloss over. The CeRAI integration also required non-trivial adaptation work (documented below) that produced genuine research value beyond the chatbot itself.

---

## Repo layout

```
fellowship-assignment/
├── chatbot/
│   ├── ingest.py          # PDF → FAISS vectorstore pipeline
│   ├── rag.py             # LangChain history-aware RAG chain
│   ├── server.py          # FastAPI app; /chat, /healthz, /v1/chat/completions
│   ├── prompts.py         # System and retrieval prompt templates
│   └── static/index.html  # Minimal browser chat UI
├── data/
│   ├── AI Fellows - ICO.pdf               # Role description (knowledge base)
│   └── Total Rewards Summary - India.pdf  # India benefits (knowledge base)
├── evaluation/
│   ├── cerai_config.json  # CeRAI config adapted for SQLite + local API target
│   ├── datapoints.json    # 30-case test suite (CeRAI JSON format)
│   ├── plans.json         # CeRAI test plan definition
│   ├── run_eval.sh        # End-to-end evaluation driver script
│   └── CERAI_NOTES.md     # Detailed notes on CeRAI internals + adaptations made
├── findings/
│   ├── index.md           # Full evaluation report (rendered by GitHub Pages)
│   ├── results.json       # Machine-readable scorecard
│   └── _config.yml        # Jekyll config for GitHub Pages
├── tests/                 # pytest test suite for ingest, rag, and server
├── .env.example           # Environment variable template
├── requirements.txt       # Python dependencies (chatbot + tests)
└── vectorstore/           # FAISS index (generated; git-ignored)
```

---

## Quickstart — run the chatbot locally

**Prerequisites:** Python 3.11+, an OpenAI API key.

```bash
# 1. Clone the repo
git clone https://github.com/<USERNAME>/fellowship-assignment.git
cd fellowship-assignment

# 2. Create and activate the virtualenv
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# 5. Ingest the PDFs (builds the FAISS vectorstore)
python -m chatbot.ingest

# 6. Start the server
uvicorn chatbot.server:app --port 9000 --reload
```

The server is ready when you see `Application startup complete`.  
Open `http://localhost:9000` in a browser for the minimal chat UI, or call the API directly.

---

## Test the chatbot

```bash
# Health check
curl http://localhost:9000/healthz

# Chat (native endpoint)
curl -s -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-1", "message": "How many AI Fellow vacancies are there?"}' \
  | python -m json.tool

# OpenAI-compatible endpoint (used by CeRAI)
curl -s -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is the OPD limit?"}], "model": "fellowship-faq"}' \
  | python -m json.tool
```

---

## Run the CeRAI evaluation

### Prerequisites

1. **Ollama** installed and running (`ollama serve` in a separate terminal).
2. **`qwen2.5:1.5b`** pulled locally (`ollama pull qwen2.5:1.5b`).
3. **CeRAI cloned as a sibling directory** (the run script looks for `../AIEvaluationTool`):

```bash
git clone https://github.com/cerai-iitm/AIEvaluationTool ../AIEvaluationTool
cd ../AIEvaluationTool
git checkout 190c1297d4c5178249b03255f3688b765128b4a5   # pinned commit used for this submission
```

4. **CeRAI virtualenv** (separate from the chatbot venv — dependency conflicts exist):

```bash
cd ../AIEvaluationTool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

   See `evaluation/CERAI_NOTES.md` for the additional patches required (`iso639` import fix,
   `lang_handler` stub, executor response-parsing patch, and interface-manager dependency installs).

5. **Chatbot running** on port 9000 (see Quickstart above).

### Run

```bash
# From the fellowship-assignment root, with the chatbot already running:
bash evaluation/run_eval.sh
```

The script:
1. Copies `evaluation/cerai_config.json` and the test data into `../AIEvaluationTool/`.
2. Imports the 30-case test suite into CeRAI's SQLite database.
3. Starts the CeRAI interface manager in the background (port 8000).
4. Executes all 30 test cases against the chatbot via `POST /v1/chat/completions`.
5. Runs LLM-as-judge scoring with `qwen2.5:1.5b`.
6. Generates a JSON + PDF report, copied back to `evaluation/reports/<run-name>/`.

You can override the run name and CeRAI path:

```bash
RUN_NAME=my-run CERAI_DIR=/path/to/AIEvaluationTool bash evaluation/run_eval.sh
```

---

## Findings

| Resource | Link |
|---|---|
| Live report (GitHub Pages) | https://\<USERNAME\>.github.io/fellowship-assignment/ |
| Report source | [`findings/index.md`](findings/index.md) |
| Machine-readable scorecard | [`findings/results.json`](findings/results.json) |
| CeRAI adaptation notes | [`evaluation/CERAI_NOTES.md`](evaluation/CERAI_NOTES.md) |

### Summary scorecard

| Dimension | Score | Cases |
|---|---|---|
| Accuracy | 0.28 / 1.00 | 10 |
| Refusal | 0.61 / 1.00 | 8 |
| Hallucination | 0.53 / 1.00 | 7 |
| Safety | 0.64 / 1.00 | 5 |
| **Overall** | **0.51 / 1.00** | **30** |

---

## AI use disclosure

Claude Code (Anthropic) was used extensively throughout this submission. The high-level approach, technical spec, implementation plan, and the majority of code (ingestion pipeline, RAG chain, FastAPI server, test suite, evaluation driver script, and findings document) were produced with Claude Code assistance and reviewed and adjusted before each commit. No generated artefact was committed without human review; all factual claims in `findings/index.md` were verified against the actual CeRAI output.

The CeRAI integration required substantial troubleshooting that Claude Code assisted with but could not resolve autonomously: the `iso639` import error required inspecting CeRAI source code to identify the correct replacement; the `lang_handler` stub was written after reading the interface-manager's call sites; the executor response-parsing patch required tracing a silent failure through three layers of CeRAI internals; and the interface-manager dependency installs required reading `ImportError` tracebacks against an unlisted requirements file. This discovery process — and what we learned about CeRAI's undocumented constraints — is the main content of `evaluation/CERAI_NOTES.md`.

---

## Known limitations

- **Accuracy is understated by the judge model.** `qwen2.5:1.5b` frequently mis-scores correct answers embedded in prose (e.g., marking a response as missing a figure that is visibly present in the text). The true factual accuracy is meaningfully higher than 0.28.
- **Small vectorstore.** Only two PDFs were ingested. Figures that appear once in running text (e.g., the vacancy count) are not reliably surfaced by top-3 retrieval.
- **No re-ranking.** Retrieval uses raw cosine similarity on `text-embedding-3-small` embeddings with no cross-encoder re-ranking step. Adding MMR or a cross-encoder would likely improve factual recall.
- **Single-turn evaluation.** CeRAI's test data format does not support multi-turn test cases; all 30 test cases are single-turn prompts, which does not exercise the history-aware retriever.
- **Local judge model only.** CeRAI's LLM-judge strategy is hard-coded to Ollama; closed-source models (OpenAI, Anthropic) cannot be used as judges without modifying CeRAI's source code. A more capable judge would reduce evaluation noise substantially.
