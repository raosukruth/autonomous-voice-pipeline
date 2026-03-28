#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

mkdir -p output
mkdir -p rounds

next_round_dir() {
	local n=1
	while [[ -d "rounds/round-${n}" ]]; do
		((n++))
	done
	echo "rounds/round-${n}"
}

STAMP="$(date +"%Y%m%d_%H%M%S")"
TEST_LOG="output/tests_${STAMP}.log"
RUN_LOG="output/run_${STAMP}.log"

if [[ "${FULL_TESTS:-0}" == "1" ]]; then
	echo "[1/2] Running full test suite..."
	echo "      Log: $TEST_LOG"
	python -m pytest src/ . -v 2>&1 | tee "$TEST_LOG"
else
	echo "[1/2] Running smoke test suite..."
	echo "      Log: $TEST_LOG"
	python -m pytest \
		src/test_config.py \
		src/test_audio_utils.py \
		src/test_logger.py \
		src/test_call_recorder.py \
		src/test_orchestrator.py \
		-q 2>&1 | tee "$TEST_LOG"
fi

echo "[2/2] Running full program..."
echo "      Log: $RUN_LOG"
python main.py 2>&1 | tee "$RUN_LOG"

ROUND_DIR="$(next_round_dir)"
mkdir -p "$ROUND_DIR/output"
cp -R output/. "$ROUND_DIR/output/"
if [[ -f STATUS.md ]]; then
	cp STATUS.md "$ROUND_DIR/STATUS.md"
fi

ROUND_RANKING="rounds/round_ranking.md"
echo "[3/3] Ranking rounds..."
echo "      Report: $ROUND_RANKING"
if python -m src.rounds_analyzer --base-dir rounds --output "$ROUND_RANKING"; then
	echo "      Round ranking generated."
else
	echo "      Round ranking failed; continuing without it."
fi

echo "Done."
echo "Reports and outputs:"
echo "- Bug report: output/bug_report.md"
echo "- Recordings: output/recordings/"
echo "- Transcripts: output/transcripts/"
echo "- Test log: $TEST_LOG"
echo "- Program log: $RUN_LOG"
echo "- Snapshot: $ROUND_DIR"
echo "- Round ranking: $ROUND_RANKING"
