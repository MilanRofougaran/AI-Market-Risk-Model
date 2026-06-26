#!/usr/bin/env bash
# Verify a just-edited code file's syntax. Runs after every Write/Edit.
# Exit 2 (block) on a real syntax error so the editor is told to fix it.
# Covers: Python (py_compile), JS/MJS (node --check), and inline <script> in HTML.
export PATH="$HOME/.local/node/bin:$PATH"

f=$(python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path') or d.get('tool_response',{}).get('filePath') or '')" 2>/dev/null)
[ -z "$f" ] && exit 0
[ -f "$f" ] || exit 0

case "$f" in
  *.py)
    out=$(python3 -m py_compile "$f" 2>&1) || { echo "❌ Python syntax error in $f:"; echo "$out"; exit 2; }
    ;;
  *.mjs|*.js)
    command -v node >/dev/null || exit 0
    out=$(node --check "$f" 2>&1) || { echo "❌ JS syntax error in $f:"; echo "$out"; exit 2; }
    ;;
  *.html)
    command -v node >/dev/null || exit 0
    tmp=$(mktemp /tmp/verify-XXXX.js)
    python3 - "$f" > "$tmp" <<'PY'
import re, sys
h = open(sys.argv[1]).read()
blocks = re.findall(r'<script(?![^>]*src=)(?![^>]*type="module")[^>]*>(.*?)</script>', h, re.S)
print("\n;\n".join(b for b in blocks if b.strip()))
PY
    out=$(node --check "$tmp" 2>&1) || { echo "❌ Inline-JS syntax error in $f:"; echo "$out"; rm -f "$tmp"; exit 2; }
    rm -f "$tmp"
    ;;
esac
exit 0
