#!/usr/bin/env bash
# Run the full CeRAI evaluation against the Fellowship FAQ chatbot.
# Prerequisites:
#   1. The chatbot must be running on port 9000:
#      source .venv/bin/activate && uvicorn chatbot.server:app --port 9000
#   2. Ollama must be running with qwen2.5:1.5b pulled:
#      ollama serve (in a separate terminal)
#   3. CeRAI cloned at ../AIEvaluationTool (sibling directory)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERAI_DIR="${CERAI_DIR:-$REPO_ROOT/../AIEvaluationTool}"
RUN_NAME="${RUN_NAME:-fellowship-eval-$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="$REPO_ROOT/evaluation/reports/$RUN_NAME"

if [ ! -d "$CERAI_DIR" ]; then
  echo "CeRAI not found at $CERAI_DIR. Clone it first:" >&2
  echo "  git clone https://github.com/cerai-iitm/AIEvaluationTool $CERAI_DIR" >&2
  exit 1
fi

# Verify chatbot is up
if ! curl -sf http://localhost:9000/healthz > /dev/null; then
  echo "Chatbot not responding at http://localhost:9000. Start it first:" >&2
  echo "  source .venv/bin/activate && uvicorn chatbot.server:app --port 9000" >&2
  exit 1
fi

# Verify Ollama is up
if ! curl -sf http://localhost:11434 > /dev/null; then
  echo "Ollama not running. Start it first: ollama serve" >&2
  exit 1
fi

echo "==> Run name: $RUN_NAME"
mkdir -p "$OUT_DIR"

# Copy our test data and config into CeRAI
cp "$REPO_ROOT/evaluation/cerai_config.json" "$CERAI_DIR/our_config.json"
mkdir -p "$CERAI_DIR/our_data"
cp "$REPO_ROOT/evaluation/datapoints.json"   "$CERAI_DIR/our_data/updated_datapoints.json"
cp "$REPO_ROOT/evaluation/plans.json"        "$CERAI_DIR/our_data/plans.json"

cd "$CERAI_DIR"
source .venv/bin/activate

echo "==> Step 1: Import test data"
python3 src/app/importer/main.py --config our_config.json

echo "==> Step 2: Start CeRAI interface manager (background)"
python3 src/app/interface_manager/main.py &
IM_PID=$!
sleep 4
echo "    Interface manager PID: $IM_PID"

echo "==> Step 3: Execute test cases (plan T1, up to 30 cases)"
python3 src/app/testcase_executor/main.py \
  --config our_config.json \
  --testplan-id 1 \
  --max-testcases 30 \
  --run-name "$RUN_NAME" \
  --execute

echo "==> Step 4: Analyze responses"
python3 src/app/response_analyzer/analyze.py \
  --config our_config.json \
  --run-name "$RUN_NAME"

echo "==> Step 5: Generate report"
python3 src/app/response_analyzer/report.py \
  --config our_config.json \
  --run-name "$RUN_NAME" \
  --get-report

echo "==> Stopping interface manager"
kill $IM_PID 2>/dev/null || true

# Copy report outputs back into our project
mkdir -p "$OUT_DIR"
if ls "$CERAI_DIR"/reports/AI_Evaluation_Report_*"$RUN_NAME"* 2>/dev/null; then
  cp "$CERAI_DIR"/reports/AI_Evaluation_Report_*"$RUN_NAME"* "$OUT_DIR/" 2>/dev/null || true
fi
echo "==> Done. Outputs at: $OUT_DIR"
echo "    To snapshot this run: cp -R $OUT_DIR $REPO_ROOT/evaluation/reports/snapshot_$(date +%Y-%m-%d)/"
