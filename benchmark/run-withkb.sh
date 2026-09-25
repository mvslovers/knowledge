#!/bin/bash
# with-KB arm. Working directory IS the KB copy (benchmark/ removed).
# Completion check is on CONTENT, not on has("result") — see §4 of the baseline
# results file: 8 of 27 baseline invocations returned has_result:true carrying
# only a narrated tool call.

Q=/home/claude/kb-q
OUT=${OUT:-/home/claude/kb-out/withkb}
KB=/home/claude/kb-with
LOG=$OUT/run.log
mkdir -p "$OUT"

# A result counts as an answer only if it clears all three:
#   - the result field exists
#   - >= 400 characters
#   - does not consist of a narrated/hallucinated tool call
answered() {
  local f=$1
  jq -e '
    has("result")
    and ((.result // "") | length) >= 400
    and ((.result // "") | test("<invoke name=|^I.ll (look|take a quick look|check)"; "i") | not)
  ' "$f" >/dev/null 2>&1
}

run_one() {
  local qid=$1 n=$2
  local f="$OUT/withkb-$qid-r$n.json"
  cd "$KB" || exit 1
  claude -p "$(cat "$Q/$qid.txt")" \
    --model claude-opus-5 \
    --output-format json \
    --disallowedTools "WebSearch,WebFetch" \
    --strict-mcp-config \
    --no-chrome \
    > "$f" 2>>"$LOG.err"
  local verdict="ANSWER"
  answered "$f" || verdict="NON-ANSWER"
  echo "$qid r$n $verdict turns=$(jq -r '.num_turns' "$f") chars=$(jq -r '(.result//"")|length' "$f") model=$(jq -r '.modelUsage|to_entries|map(select(.value.outputTokens>100))|map(.key)|join(",")' "$f") cost=$(jq -r '.total_cost_usd' "$f")" >> "$LOG"
}

for spec in "$@"; do
  qid=${spec%:*}; n=${spec#*:}
  run_one "$qid" "$n" &
done
wait
echo "DONE" >> "$LOG"
