#!/usr/bin/env bash
#
# Tripwires for defects this repository has actually had. Each one was real;
# each is here so it fails loudly next time instead of quietly.
#
# Usage: ops/hygiene.sh

set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

FAILURES=0
check() {
    local label="$1"; shift
    if "$@"; then
        printf 'ok   %s\n' "$label"
    else
        printf 'FAIL %s\n' "$label"
        FAILURES=$((FAILURES + 1))
    fi
}

# Tracked files PLUS new files that are not gitignored. `git ls-files` alone
# lists only what is committed, so a brand new file - the kind most likely to
# be wrong - would be skipped on a local run.
repo_files() {
    git ls-files --cached --others --exclude-standard
}

# `! cmd | xargs grep | grep .` is not reliable under `set -o pipefail`: xargs
# returns non-zero when one batch has no match, which makes the whole pipeline
# non-zero and the negation report success while printing the matches it found.
# Collect the output and test it instead.
expect_no_matches() {
    local hits
    hits=$(eval "$1" 2>/dev/null)
    [ -z "$hits" ] && return 0
    echo "$hits" | head -20 | sed 's/^/  /'
    return 1
}

# Four test files and an admin dashboard were committed as zero bytes, so the
# repo looked tested and looked like it had a dashboard. Package markers are
# the only files allowed to be empty.
no_empty_source_files() {
    local bad=0 f
    for f in $(repo_files | grep -E '\.(py|sh)$'); do
        if [ ! -s "$f" ] && [ "$(basename "$f")" != "__init__.py" ]; then
            echo "  empty file: $f"
            bad=1
        fi
    done
    [ "$bad" -eq 0 ]
}

# The kiosk runs unattended. A repo-relative resource opened through a bare
# relative path works under the systemd unit (which sets WorkingDirectory) and
# fails everywhere else, mid-turn.
resources_use_repo_relative_paths() {
    # Both spellings: Path("llm/...") and the bare open("config.yaml") that the
    # first version of this check missed entirely.
    expect_no_matches "repo_files | grep -E '\.py\$' | grep -v '^tests/' | xargs grep -nE '(Path|open)\(\"(llm|admin|knowledge_base|tts)/|open\(\"config\.yaml\"'"
}

# Credentials.
no_env_or_keys_committed() {
    repo_files | grep -qE '(^|/)\.env$' && { echo "  .env is tracked"; return 1; }
    expect_no_matches "repo_files | grep -vE '^ops/hygiene\.sh\$' | xargs grep -lnE 'gsk_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}'"
}

# Every prompt the code formats must exist. A missing one raised
# FileNotFoundError from inside the crisis path.
prompt_files_exist() {
    local missing=0 name
    for name in system_emotional system_friend system_institutional system_rolebase; do
        [ -f "llm/prompts/${name}.txt" ] || { echo "  missing llm/prompts/${name}.txt"; missing=1; }
    done
    [ "$missing" -eq 0 ]
}

# The kiosk advertises English, Hindi and Telugu. The crisis keyword list was
# English only, so a crisis in the other two scored "neutral" and never even
# reached the LLM triage.
crisis_phrases_cover_every_language() {
    # No `grep -q` shortcut here. It searched the whole file, so the
    # Devanagari still present in STRESS_PHRASES satisfied it and it
    # short-circuited past the real check, reporting ok with every Hindi
    # and Telugu crisis phrase deleted.
    python3 - modules/emotional_support.py <<'PY'
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
block = src[src.index("CRISIS_PHRASES"):src.index("STRESS_PHRASES")]
has_devanagari = bool(re.search(r"[ऀ-ॿ]", block))
has_telugu = bool(re.search(r"[ఀ-౿]", block))
problems = []
if not has_devanagari:
    problems.append("no Hindi (Devanagari) crisis phrases")
if not has_telugu:
    problems.append("no Telugu crisis phrases")
for p in problems:
    print(f"  {p}")
sys.exit(1 if problems else 0)
PY
}

# The escalation must not depend on the LLM call succeeding. It used to be
# appended only after a successful llm.chat(), so a timeout meant the student
# heard nothing at all.
crisis_escalation_survives_an_llm_failure() {
    grep -q '_crisis_fallback' modules/emotional_support.py &&
    grep -q 'def counsellor_details' modules/emotional_support.py
}

# One failed turn must not take the kiosk down. There was no handler at all, so
# a single LLM timeout killed the process and systemd spent a minute reloading
# Whisper and Chroma before it could listen again.
a_failed_turn_does_not_kill_the_loop() {
    grep -A4 '_handle_turn(capture)' core/pipeline.py | grep -q 'except Exception' ||
    grep -B6 'Turn failed' core/pipeline.py | grep -q 'try:'
}

# House style: no em dashes, en dashes or emoji in anything tracked.
no_decorative_glyphs() {
    expect_no_matches "repo_files | grep -vE '\.(png|jpg|jpeg|gif|svg|ico)\$' | xargs grep -nP '[\x{2013}\x{2014}\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{FE0F}]'"
}

config_is_complete() {
    python3 ops/check_config.py > /dev/null
}

check "no empty source files"                      no_empty_source_files
check "repo resources use repo-relative paths"     resources_use_repo_relative_paths
check "no .env or API keys committed"              no_env_or_keys_committed
check "every prompt file exists"                   prompt_files_exist
check "crisis phrases cover en, hi and te"         crisis_phrases_cover_every_language
check "crisis escalation survives an LLM failure"  crisis_escalation_survives_an_llm_failure
check "a failed turn does not kill the loop"       a_failed_turn_does_not_kill_the_loop
check "no em dashes, en dashes or emoji"           no_decorative_glyphs
check "config.yaml has every key the code reads"   config_is_complete

echo
if [ "$FAILURES" -eq 0 ]; then
    echo "hygiene: all checks passed"
else
    echo "hygiene: ${FAILURES} check(s) failed"
fi
exit "$FAILURES"
