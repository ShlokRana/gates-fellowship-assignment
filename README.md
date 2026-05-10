# Gates Foundation AI Fellowship India 2026 — Technical Assignment

**Author:** Shlok Rana  
**Option:** A — Evaluate & Report  
**Live findings:** https://ShlokRana.github.io/gates-fellowship-assignment/  
**Repository:** https://github.com/ShlokRana/gates-fellowship-assignment  
**CeRAI fork used:** https://github.com/ShlokRana/AIEvaluationTool _(patched for macOS M1 — see below)_

---

## What this is

Option A submission for the Gates Foundation AI Fellowship India 2026 technical assignment.

A basic RAG FAQ chatbot was built and grounded in two official Gates Foundation program documents — the AI Fellow role description and the India Total Rewards Summary. The chatbot was then evaluated end-to-end using the **CeRAI AI Evaluation Tool** (a real open-source evaluation framework from IIT Madras). The findings document at the link above is the primary deliverable required by the assignment.

---

## Path chosen

Option A was chosen because it produces a complete, honest audit trail: the same artefacts that demonstrate what the chatbot can do also expose what it gets wrong, measured with an independent third-party tool. CeRAI is a real framework designed for this class of problem. Using it — rather than writing evaluation code ourselves — means the evaluation methodology is not invented for this submission.

The CeRAI integration also required non-trivial adaptation work on macOS M1 (documented in detail below and in `evaluation/CERAI_NOTES.md`). That troubleshooting process itself produced research value: we discovered undocumented constraints and bugs in CeRAI's API flow that are directly relevant to the assignment's goal of understanding the tool's scope and limitations.

---

## Repo layout

```
gates-fellowship-assignment/
├── chatbot/
│   ├── ingest.py           # PDF → FAISS vectorstore pipeline
│   ├── rag.py              # LangChain history-aware RAG chain (GPT-3.5-turbo)
│   ├── server.py           # FastAPI: /chat, /healthz, /v1/chat/completions (OAI-compat)
│   ├── prompts.py          # System prompt + history-condense prompt templates
│   └── static/index.html   # Minimal browser chat UI (sanity-checks only)
│
├── data/
│   ├── AI Fellows - ICO.pdf               # Role description (knowledge base)
│   └── Total Rewards Summary - India.pdf  # India benefits + compensation (knowledge base)
│
├── evaluation/
│   ├── cerai_config.json   # CeRAI config: SQLite DB, API target at localhost:9000
│   ├── datapoints.json     # 30-case test suite in CeRAI's JSON format
│   ├── plans.json          # CeRAI test plan definition (4 metrics)
│   ├── run_eval.sh         # End-to-end evaluation driver (5-stage CeRAI pipeline)
│   ├── CERAI_NOTES.md      # Full discovery notes on CeRAI internals and what we changed
│   └── reports/
│       └── snapshot_2026-05-10/  # Committed CeRAI run cited in findings
│           ├── evaluation_report.json
│           └── fellowship_eval.db
│
├── findings/
│   ├── index.html          # Beautiful HTML evaluation report (GitHub Pages primary file)
│   ├── index.md            # Markdown version of the same report
│   ├── results.json        # Machine-readable scorecard
│   └── _config.yml         # GitHub Pages Jekyll config
│
├── tests/                  # pytest suite: test_ingest, test_rag, test_server
├── docs/                   # Design spec + implementation plan (generated during build)
├── .env.example            # Environment variable template
└── requirements.txt        # Python dependencies (chatbot + tests)
```

---

## Quickstart — run the chatbot locally

**Prerequisites:** Python 3.11+, an OpenAI API key.

```bash
# 1. Clone
git clone https://github.com/ShlokRana/gates-fellowship-assignment.git
cd gates-fellowship-assignment

# 2. Create virtualenv and install deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Open .env and set: OPENAI_API_KEY=sk-...

# 4. Build FAISS vectorstore from the two PDFs
python -m chatbot.ingest

# 5. Start the chatbot (port 9000 — CeRAI connects here)
uvicorn chatbot.server:app --port 9000
```

Open `http://localhost:9000` for the browser chat UI, or use curl:

```bash
# Health check
curl http://localhost:9000/healthz

# Native chat endpoint
curl -s -X POST http://localhost:9000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"demo","message":"What is the maximum maternity care benefit?"}' | python -m json.tool

# OpenAI-compatible endpoint (used by CeRAI internally)
curl -s -X POST http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"How many AI Fellow vacancies are there?"}],"model":"fellowship-faq"}' | python -m json.tool
```

---

## Run the CeRAI evaluation

### Why there is a separate CeRAI fork

CeRAI is an excellent framework but was developed primarily for WhatsApp and Selenium-based web targets. Getting it to evaluate a local FastAPI chatbot on macOS M1 required five targeted patches. We forked the repo, applied the patches as clean commits with explanatory messages, and pinned the SHA. **Our fork is at https://github.com/ShlokRana/AIEvaluationTool** — clone that instead of the upstream to avoid having to apply patches manually.

### Step-by-step evaluation setup

**Step 1 — Install Ollama and pull the judge model**

CeRAI's LLM-as-judge runs exclusively through Ollama (not OpenAI or Anthropic — this is a CeRAI design constraint documented in `evaluation/CERAI_NOTES.md`). We use `qwen2.5:1.5b` because it fits in 8 GB RAM.

```bash
# macOS
brew install ollama
ollama pull qwen2.5:1.5b

# Start Ollama (keep running in a separate terminal)
ollama serve
```

**Step 2 — Clone our patched CeRAI fork**

```bash
git clone https://github.com/ShlokRana/AIEvaluationTool ../AIEvaluationTool
```

This must be a **sibling directory** of this repo (the run script looks for `../AIEvaluationTool`).

**Step 3 — Set up CeRAI's Python environment**

CeRAI has dependency conflicts with the chatbot (different langchain versions), so it needs its own virtualenv:

```bash
cd ../AIEvaluationTool
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install randomname google-genai selenium psutil webdriver-manager weasyprint
```

**Step 4 — Configure CeRAI's environment**

```bash
cp .env.example .env
```

Edit `.env` and set:

```
OPENAI_API_KEY=sk-your-key-here    # same key used by the chatbot
OLLAMA_URL=http://localhost:11434   # Ollama running locally
LLM_AS_JUDGE_MODEL=qwen2.5:1.5b    # must match what you pulled
```

Also create `src/lib/strategy/.env` with the same content plus:

```
DEFAULT_VALUES_PATH=data/defaults.json
```

**Step 5 — Run the evaluation**

With the chatbot running on port 9000 and Ollama running in another terminal:

```bash
cd /path/to/gates-fellowship-assignment
bash evaluation/run_eval.sh
```

The script runs the 5-stage CeRAI pipeline:
1. Imports the 30 test cases into CeRAI's SQLite DB
2. Starts CeRAI's interface manager (port 8000) in the background
3. Executes all 30 cases against the chatbot via `POST /v1/chat/completions`
4. Scores each response with `qwen2.5:1.5b` as LLM judge
5. Generates a JSON report in `evaluation/reports/<run-name>/`

---

## What we changed in CeRAI — and why

This section is the key supporting document for the reviewer. All changes are in our fork at https://github.com/ShlokRana/AIEvaluationTool. Full context is in `evaluation/CERAI_NOTES.md`.

### Change 1 — `src/lib/strategy/data/defaults.json`

**What:** Changed `"qwen3:32b"` to `"qwen2.5:1.5b"` in three places.

**Why:** CeRAI's default judge model is `qwen3:32b` — a 32-billion-parameter model that requires ~40 GB RAM. This cannot run on a MacBook Air M1 with 8 GB. `qwen2.5:1.5b` is a 1.5B-parameter model (~1 GB) that runs comfortably on M1 and still produces LLM-as-judge outputs in JSON format as required by CeRAI's GEval integration.

### Change 2 — `src/lib/utils/lang_handler.py`

**What:** Replaced the file with a lightweight stub that returns English-language constants.

**Why:** The original file imports `googletrans`, which hardcodes `httpcore 0.9.x` as a dependency. CeRAI's other packages (openai, langchain) require `httpcore >=1.0`. The two versions are mutually incompatible on the same Python environment. Since all our test cases are in English and we never call translation functions, stubbing the module avoids the conflict entirely without affecting evaluation correctness. The stub preserves the full public interface (`lang_translate`, `lang_detect`, `iso639_to_language_name`, `language_name_to_iso639`) so nothing downstream breaks.

### Change 3 — `src/lib/strategy/utils_new.py`

**What:** Wrapped `from weasyprint import HTML` in a `try/except` block.

**Why:** `weasyprint` requires `libgobject` (a GTK system library) for PDF rendering. GTK is not installed on macOS by default and requires `brew install gtk+3` (a multi-GB system package). PDF report generation is optional — CeRAI's JSON report is produced before the PDF step, and the JSON is what we care about. The try/except lets everything else in `utils_new.py` load normally; if PDF generation is attempted, it will fail gracefully rather than preventing the entire evaluation pipeline from importing.

### Change 4 — `src/app/importer/main.py`

**What:** Appended 6 lines at the end of the script to register `FellowshipChatbot` as a target.

**Why:** CeRAI's importer has a hardcoded list of 9 target applications (all WhatsApp bots or web apps for specific projects at IIT Madras). The importer `add_or_get_target()` call creates the target record in SQLite; without it, the testcase executor cannot find a target to evaluate against and exits with an error. Adding our target to the importer is the documented mechanism for onboarding a new evaluation target — CeRAI does not provide a config-based target registration path.

### Change 5 — `src/app/testcase_executor/main.py`

**What:** Two patches:
1. Fixed `is_error_response()` to handle string inputs (added `isinstance(response, str)` branch).
2. Changed `conv.agent_response = agent_response[0]['response']` to `conv.agent_response = agent_response if isinstance(agent_response, str) else agent_response[0]['response']` at three locations.

**Why:** CeRAI's API handler (`api_handler.py`) was updated at some point to return `{"type": "text", "content": "..."}` as the inner response object, but the testcase executor was not updated to match. The executor expected `agent_response` to be a list of dicts (`[{"response": "..."}]`) but was receiving a plain string (the extracted text content). This caused a silent `"string indices must be integers, not 'str'"` error on every test case, recorded all results as `FAILED` with no judge scoring. Fixing the type handling in `is_error_response` and `conv.agent_response` allows the extracted chatbot response string to pass through correctly to the LLM judge.

---

## Findings

| Resource | Link |
|---|---|
| **Live report** | https://ShlokRana.github.io/gates-fellowship-assignment/ |
| Report source (HTML) | [`findings/index.html`](findings/index.html) |
| Report source (Markdown) | [`findings/index.md`](findings/index.md) |
| Machine-readable scorecard | [`findings/results.json`](findings/results.json) |
| CeRAI adaptation notes | [`evaluation/CERAI_NOTES.md`](evaluation/CERAI_NOTES.md) |
| Committed evaluation run | [`evaluation/reports/snapshot_2026-05-10/`](evaluation/reports/snapshot_2026-05-10/) |

### Scorecard (CeRAI · qwen2.5:1.5b judge · 30 cases)

| Dimension | Score | Cases | Note |
|---|---|---|---|
| Accuracy | 0.28 / 1.00 | 10 | Low partly due to judge false negatives; see report |
| Refusal | 0.61 / 1.00 | 8 | 2 zero-scores are tooling artefacts, not chatbot failures |
| Hallucination | 0.53 / 1.00 | 7 | HAL_01–03 scored 0 despite correct refusals (judge inversion bug) |
| Safety | 0.64 / 1.00 | 5 | Strongest reliable dimension |
| **Overall** | **0.51 / 1.00** | **30** | |

---

## AI use disclosure

Claude Code (Anthropic) was used extensively throughout this submission: the technical spec, implementation plan, RAG chatbot (ingest/chain/server), test suite, evaluation driver script, and findings document were all produced with Claude Code assistance and reviewed before commit. No generated artefact was committed without human review; all factual claims in the findings were verified against the actual CeRAI output.

The CeRAI integration required substantial troubleshooting that Claude Code assisted with but could not resolve autonomously — reading CeRAI source code to diagnose import failures, tracing a silent executor bug through three layers of code, and identifying the `api_handler.py` ↔ `testcase_executor.py` interface mismatch. This discovery process is the main content of `evaluation/CERAI_NOTES.md` and is what the assignment means by "Understanding the scope and limitations of the tool is itself part of the task."

---

## Known limitations

- **Judge model accuracy:** `qwen2.5:1.5b` at 1.5B parameters produces systematic scoring inconsistencies (correct reasoning, wrong score). CeRAI's judge is Ollama-only by design; a frontier model judge would produce significantly more reliable results.
- **Small retrieval k:** Top-3 retrieval misses facts embedded in narrative prose (e.g., vacancy count). Increasing k to 5–6 would improve recall.
- **Single-turn only:** CeRAI's test format is one prompt per case; the chatbot's history-aware retriever was not exercised.
- **Two documents only:** Evaluation is specific to this two-PDF corpus; adding documents would require re-indexing and re-evaluation.
- **English only:** All test cases are in English; multilingual robustness was not tested.
