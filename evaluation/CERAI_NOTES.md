# CeRAI Discovery Notes

## Git SHA

Commit: `190c1297d4c5178249b03255f3688b765128b4a5`
Repo: https://github.com/cerai-iitm/AIEvaluationTool
Cloned to: `/Users/shlokrana/shlok-project/AIEvaluationTool`

---

## 1. Shared `config.json` Schema (repository root)

All four CLI tools (importer, testcase_executor, response_analyzer, report.py) read from
the **repository-level** `config.json`. The actual file in the repo at commit `190c129` is:

```json
{
    "db": {
        "engine": "mariadb",
        "host": "db",
        "port": 3306,
        "user": "aiet_user",
        "password": "aiet_password",
        "database": "aievaluationtool"
    },
    "examples": {
        "db_1": {
            "engine": "mariadb",
            "host": "db",
            "port": 3306,
            "user": "aiet_user",
            "password": "aiet_password",
            "database": "aievaluationtool"
        },
        "db_2": {
            "engine": "sqlite",
            "file": "example.db"
        }
    },
    "files": {
        "plans": "data/plans.json",
        "testcases": "data/updated_datapoints.json",
        "strategies": "data/strategy_id.json"
    },
    "target": {
        "application_type": "WHATSAPP_WEB",
        "application_name": "Vaidya AI",
        "application_url": "https://web.whatsapp.com/",
        "agent_name": "Vaidya AI"
    },
    "interface_manager": {
        "docker": true,
        "base_url": "http://interface-manager:8000",
        "base_url_local": "http://localhost:8000"
    },
    "port": {
        "back-end": "7000",
        "interface-manager": "8000"
    }
}
```

### For an API target (our chatbot), adapted version:

```json
{
    "db": {
        "engine": "sqlite",
        "file": "AIEvaluationData.db"
    },
    "files": {
        "plans": "data/plans.json",
        "testcases": "data/updated_datapoints.json",
        "strategies": "data/strategy_id.json"
    },
    "target": {
        "application_type": "API",
        "application_name": "FellowshipChatbot",
        "application_url": "http://host.docker.internal:8000",
        "agent_name": "FellowshipChatbot"
    },
    "interface_manager": {
        "docker": false,
        "base_url": "http://localhost:8000",
        "base_url_local": "http://localhost:8000"
    }
}
```

### Key `db.engine` values:
- `"sqlite"` → requires `"file": "<filename>.db"` (stored under `data/<filename>.db`)
- `"mariadb"` → requires `host`, `port`, `user`, `password`, `database`

### Key `target.application_type` values (from source code):
- `"API"` — REST/HTTP endpoint (auto-detected as LOCAL, OPENAI, or GEMINI based on `agent_name` and `application_url`)
- `"WHATSAPP_WEB"` — WhatsApp Web via Selenium
- `"WEBAPP"` — Web application via Selenium

### `interface_manager.docker`:
- `true` → uses `base_url` (e.g., `http://interface-manager:8000`) — the Docker network address
- `false` → hardcodes `http://localhost:8000` in the testcase executor (ignores `base_url`)

---

## 2. Test Data Format (NOT CSV — it is JSON)

**CRITICAL DISCOVERY**: CeRAI does NOT use CSV files for test cases. The importer reads
**JSON** files. The `files.testcases` key in `config.json` points to a JSON file (default:
`data/updated_datapoints.json`).

### JSON structure for `testcases` file (`updated_datapoints.json`):

```json
{
    "<metric_id_string>": {
        "cases": [
            {
                "PROMPT_ID": "P001",
                "LLM_AS_JUDGE": "No",
                "SYSTEM_PROMPT": "You are a helpful assistant.",
                "PROMPT": "What is photosynthesis?",
                "EXPECTED_OUTPUT": "Photosynthesis is...",
                "DOMAIN": "education",
                "LANGUAGE": "english",
                "STRATEGY": ["15"],
                "SUB_METRIC": "toxicity_level/contextual_or_conversational_toxicity"
            }
        ]
    }
}
```

### Field definitions (from `src/app/importer/main.py`):
- `PROMPT_ID` (str, required): unique name for the test case
- `SYSTEM_PROMPT` (str, required): system prompt text
- `PROMPT` (str, required): user prompt (maps to `Prompt.user_prompt`)
- `EXPECTED_OUTPUT` (str, optional): ground-truth response for reference-based strategies
- `LLM_AS_JUDGE` (str, required): either `"No"` or the LLM judge instruction string
- `DOMAIN` (str, optional): domain name (e.g., `"general"`, `"healthcare"`, `"agriculture"`)
- `LANGUAGE` (str, optional): language name (e.g., `"english"`)
- `STRATEGY` (list of str, optional): list of strategy IDs referencing `strategy_id.json`
- `SUB_METRIC` (str, optional): `"metric_name/sub_metric_name"` format; `"nan"` for none

### JSON structure for `plans` file (`plans.json`):

```json
{
    "T1": {
        "TestPlan_name": "Responsible_AI",
        "metrics": {
            "2": "Inclusivity",
            "3": "Transparency"
        }
    }
}
```

### JSON structure for `strategies` file (`strategy_id.json`):
A flat mapping of strategy ID string to strategy name string.

---

## 3. API Provider Auto-Detection Logic

Source: `src/lib/interface_manager/client.py`, method `_auto_detect_provider()`:

- If `application_url` starts with `http://localhost`, `http://127.0.0.1`, or
  `http://host.docker.internal` → provider is `LOCAL`
- If `agent_name` starts with `gemini` → provider is `GEMINI`
- If `agent_name` starts with `gpt` or `o` → provider is `OPENAI`
- Otherwise → RuntimeError

### LOCAL provider behavior:
Uses OpenAI-compatible API: calls `{application_url}/v1/chat/completions`.

**IMPLICATION for our chatbot**: Our FastAPI chatbot exposes `POST /chat` (not `/v1/chat/completions`).
CeRAI's LOCAL provider will try to call `http://host.docker.internal:8000/v1/chat/completions`.
This will fail unless we add an OpenAI-compatible endpoint to our chatbot.

### OPENAI provider behavior:
Uses `openai.OpenAI()` client directly (calls OpenAI's API, NOT our chatbot).

---

## 4. Multi-Turn Support

UNCLEAR from code review. The `InterfaceManagerClient` maintains `self.conversations` (a
`defaultdict(list)`) keyed by `chat_id`, which suggests multi-turn memory is tracked on the
client side. However, the testcase executor sends each test case as a single-turn prompt
(system_prompt + user_prompt concatenated as one message). There is no mechanism in the
documented plans.json or updated_datapoints.json to chain multiple turns in one test case.
**Assessment: No multi-turn plans in the current test data format.**

---

## 5. CLI Commands (in order)

All commands are run from the **repository root** of AIEvaluationTool.

### Step 1: Import test data

```bash
python3 src/app/importer/main.py --config "config.json"
```

With ORM debug logging:
```bash
python3 src/app/importer/main.py --config "config.json" --orm-debug
```

### Step 2: Start Interface Manager (runs as a FastAPI server on port 8000)

```bash
python3 src/app/interface_manager/main.py
```

(Keep running in a separate terminal — the testcase executor calls it via HTTP.)

### Step 3: List available plans (discovery)

```bash
python3 src/app/testcase_executor/main.py --config "config.json" --get-plans
python3 src/app/testcase_executor/main.py --config "config.json" --get-metrics
python3 src/app/testcase_executor/main.py --config "config.json" --get-targets
```

### Step 4: Execute test cases

Basic (runs up to 10 test cases for plan ID 1):
```bash
python3 src/app/testcase_executor/main.py --config "config.json" --testplan-id 1 --execute
```

With run name and max count:
```bash
python3 src/app/testcase_executor/main.py \
  --config "config.json" \
  --testplan-id 1 \
  --max-testcases 30 \
  --run-name "my-eval-run" \
  --execute
```

Continue existing run:
```bash
python3 src/app/testcase_executor/main.py \
  --config "config.json" \
  --testplan-id 1 \
  --run-continue \
  --run-name "my-eval-run" \
  --execute
```

### Step 5: Analyze responses

```bash
python3 src/app/response_analyzer/analyze.py --config "config.json" --run-name <run-name>
```

Force re-run:
```bash
python3 src/app/response_analyzer/analyze.py --config "config.json" --run-name <run-name> --force
```

### Step 6: Generate report

```bash
python3 src/app/response_analyzer/report.py --config "config.json" --run-name <run-name> --get-report
```

List available runs:
```bash
python3 src/app/response_analyzer/report.py --config "config.json" --get-runs
```

---

## 6. Report Output Location

From `src/app/response_analyzer/report.py` (lines 283-327):

- Reports folder: `<project_root>/reports/` (created automatically)
- JSON report: `reports/AI_Evaluation_Report_<target_name>_<run_name>.json`
- PDF report: `reports/AI_Evaluation_Report_<target_name>_<run_name>.pdf`

Where `<project_root>` = the AIEvaluationTool repository root (3 levels up from report.py).

The score_card JSON is always written; the PDF is only written when `--get-report` flag is used.

---

## 7. `LLM_AS_JUDGE_MODEL` and `gpt-4o-mini`

The env var `LLM_AS_JUDGE_MODEL` is read in `src/lib/strategy/_rag_modules.py` and passed to
`ChatOllama(model=os.getenv("LLM_AS_JUDGE_MODEL"), ...)`.

**In `src/lib/strategy/llm_judge.py`**: `LLMJudgeStrategy` does NOT use `LLM_AS_JUDGE_MODEL`
directly — it reads `model_names` from `src/lib/strategy/data/defaults.json` which is hardcoded
to `["qwen3:32b"]` (an Ollama model). It creates `CustomOllamaModel` instances.

**CONCLUSION**: `gpt-4o-mini` is NOT a valid value for `LLM_AS_JUDGE_MODEL` as-used by the
`llm_judge` strategy, which expects an Ollama model name. It is used in `_rag_modules.py`'s
`ChatOllama` constructor (also Ollama-only). The `.env.example` shows `LLM_AS_JUDGE_MODEL="qwen3:32b"` as the default.

However, `OPENAI_API_KEY` IS read by the lib interface_manager client for the OPENAI provider,
and the testcase executor passes prompts through the OPENAI API when agent_name starts with "gpt".
So `gpt-4o-mini` is a valid model for **target evaluation** (as the chatbot-under-test), NOT as
the judge model.

---

## 8. Docker Status

Docker Desktop is **not installed** on this machine. `docker` command not found.
Docker build was not possible.

The Docker Compose stack includes:
- `aiet-db` (MariaDB 11)
- `aiet-selenium` (Selenium Chrome)
- `aiet-interface-manager` (FastAPI, port 8000)
- `aiet-auth-service` (FastAPI, port 7500)
- `aiet-app-backend` (FastAPI, port 7000)
- `aiet-tdms-backend` (FastAPI, port 7250)
- `aiet-app-frontend` (React)
- `aiet-tdms-frontend` (Vue/Vite)
- `aiet-nginx` (port 80, reverse proxy)

For our use case (CLI-only pipeline), Docker is NOT required. We can run:
- SQLite instead of MariaDB
- The interface_manager locally (`python3 src/app/interface_manager/main.py`)
- All CLI scripts locally with `--config "config.json"`

---

## 9. Key Surprises vs. Spec Assumptions

1. **Test cases are JSON, not CSV.** The spec assumed CSV. CeRAI uses JSON with a specific
   nested structure (`{ "<metric_id>": { "cases": [ {...} ] } }`). No CSV import exists.

2. **No direct custom-endpoint support for our chatbot.** The `API` application_type auto-detects
   provider from `agent_name` and `application_url`. For a custom FastAPI chatbot at
   `http://localhost:8000/chat`, CeRAI will try to call `/v1/chat/completions` (OpenAI-compat).
   Our chatbot needs to expose an OpenAI-compatible `/v1/chat/completions` endpoint, OR we add
   a shim, OR we run the chatbot as a "LOCAL" provider pointing to localhost.

3. **`LLM_AS_JUDGE_MODEL` is for Ollama.** The env var expects an Ollama model name, not an
   OpenAI model. The `llm_judge` strategy uses `CustomOllamaModel` backed by deepeval's `GEval`.

4. **The importer has hardcoded target registrations.** `src/app/importer/main.py` adds 9
   specific WhatsApp/Web targets at the end of the script. A custom target for our chatbot must
   be added to this file or registered via another mechanism.

5. **Run names are randomly generated** (using `randomname` library, e.g., `doodle-accepting-pascal-nibh`).
   You can override with `--run-name`.

6. **`--max-testcases` defaults to 10.** You must explicitly pass `--max-testcases N` to run more.

7. **SQLite is fully supported** and simpler than MariaDB for local runs. The `db.engine: "sqlite"`
   path creates the DB at `data/<file>` relative to the project root.
