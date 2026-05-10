# Evaluation: running CeRAI against the chatbot

## Prerequisites

- Python 3.10+ with `pip`
- The chatbot service running on `http://localhost:8000` (see top-level README)
- An `OPENAI_API_KEY` in `.env`
- CeRAI cloned as a sibling directory:
  ```
  git clone https://github.com/cerai-iitm/AIEvaluationTool ../AIEvaluationTool
  ```
- Python dependencies installed in the AIEvaluationTool repo:
  ```
  cd ../AIEvaluationTool
  python3 -m venv venv && source venv/bin/activate
  pip install -r requirements.txt
  ```

## CeRAI version used

- Commit SHA: `190c1297d4c5178249b03255f3688b765128b4a5`

## Important: CeRAI uses JSON test data, not CSV

CeRAI's importer reads JSON files, not CSV. Test cases are authored in
`data/updated_datapoints.json` with this structure:

```json
{
    "<metric_id>": {
        "cases": [
            {
                "PROMPT_ID": "P001",
                "LLM_AS_JUDGE": "No",
                "SYSTEM_PROMPT": "You are a helpful assistant.",
                "PROMPT": "What is the topic about?",
                "EXPECTED_OUTPUT": "The topic is about...",
                "DOMAIN": "general",
                "LANGUAGE": "english",
                "STRATEGY": ["15"]
            }
        ]
    }
}
```

## How CeRAI reaches the chatbot

CeRAI's `API` application type auto-detects the provider:

- If `application_url` starts with `http://localhost` or `http://host.docker.internal` → `LOCAL` provider
- `LOCAL` provider calls `{application_url}/v1/chat/completions` (OpenAI-compatible endpoint)

**Our chatbot needs an OpenAI-compatible `/v1/chat/completions` endpoint.**
See `chatbot/` for the implementation.

## `config.json` for the chatbot target (place in AIEvaluationTool root)

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
        "application_url": "http://localhost:8000",
        "agent_name": "FellowshipChatbot"
    },
    "interface_manager": {
        "docker": false,
        "base_url": "http://localhost:8000",
        "base_url_local": "http://localhost:8000"
    }
}
```

## `.env` for AIEvaluationTool (place in AIEvaluationTool root)

```env
OLLAMA_URL=""
GPU_URL=""
LLM_AS_JUDGE_MODEL="qwen3:32b"
OPENAI_API_KEY="your_openai_api_key"
```

Note: `LLM_AS_JUDGE_MODEL` expects an Ollama model name (used by the llm_judge strategy).
`gpt-4o-mini` is NOT valid here — it requires Ollama. For LLM-as-judge strategies, you need
an Ollama instance running with a model like `qwen3:32b`.

## Running the evaluation

```bash
bash evaluation/run_eval.sh
```

## CeRAI CLI reference (for manual runs)

All commands run from `../AIEvaluationTool` directory.

### 1. Import test data

```bash
python3 src/app/importer/main.py --config "config.json"
```

### 2. Start Interface Manager (keep running)

```bash
python3 src/app/interface_manager/main.py
```

### 3. List available plans and metrics

```bash
python3 src/app/testcase_executor/main.py --config "config.json" --get-plans
python3 src/app/testcase_executor/main.py --config "config.json" --get-metrics
python3 src/app/testcase_executor/main.py --config "config.json" --get-targets
```

### 4. Execute test cases

```bash
python3 src/app/testcase_executor/main.py \
  --config "config.json" \
  --testplan-id <plan-id> \
  --max-testcases 30 \
  --run-name "fellowship-eval-2026-05-10" \
  --execute
```

### 5. Analyze responses

```bash
python3 src/app/response_analyzer/analyze.py \
  --config "config.json" \
  --run-name "fellowship-eval-2026-05-10"
```

### 6. Generate report

```bash
python3 src/app/response_analyzer/report.py \
  --config "config.json" \
  --run-name "fellowship-eval-2026-05-10" \
  --get-report
```

## Output location

Reports are written to `../AIEvaluationTool/reports/`:

- JSON: `AI_Evaluation_Report_<target_name>_<run_name>.json`
- PDF: `AI_Evaluation_Report_<target_name>_<run_name>.pdf`

Copy reports to this project:

```bash
cp ../AIEvaluationTool/reports/AI_Evaluation_Report_*.json evaluation/reports/
```

## Snapshotted run

- `evaluation/reports/snapshot_2026-05-10/`

## See also

- `evaluation/CERAI_NOTES.md` — full discovery notes including schema, surprises, and limitations
- `evaluation/run_eval.sh` — automated run script (Task 8)
- `evaluation/testcases/` — the 30-case test suite (Task 9)
