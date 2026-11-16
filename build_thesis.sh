#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

for program in python3 pdflatex biber; do
    command -v "$program" >/dev/null 2>&1 || {
        printf 'Required program not found: %s\n' "$program" >&2
        exit 1
    }
done

# TeX silently skips missing include files, so reject an incomplete checkout first.
python3 - <<'PY'
from pathlib import Path
import re
source = re.sub(r'(?m)(?<!\\)%.*', '', Path('ClassicThesis.tex').read_text())
missing = [name + '.tex' for name in re.findall(r'\\include\{([^}]+)\}', source)
           if not Path(name + '.tex').is_file()]
if missing:
    raise SystemExit('Missing chapter sources; push these files before building:\n' + '\n'.join(missing))
PY

output_dir="$PWD/build"
mkdir -p "$output_dir/Chapters" "$output_dir/FrontBackmatter"

# Some macOS Biber universal binaries have a broken bundled launcher. Extract
# the native architecture into a temporary file without changing TeX Live.
biber_command=$(command -v biber)
biber_tmp_dir=''
trap 'if [[ -n "$biber_tmp_dir" ]]; then rm -rf "$biber_tmp_dir"; fi' EXIT
if [[ $(uname -s) == Darwin ]] && command -v lipo >/dev/null 2>&1; then
    biber_archs=$(lipo -archs "$biber_command" 2>/dev/null || true)
    if [[ "$biber_archs" == *' '* ]]; then
        biber_tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/thesis-biber.XXXXXX")
        lipo "$biber_command" -thin "$(uname -m)" -output "$biber_tmp_dir/biber"
        chmod +x "$biber_tmp_dir/biber"
        biber_command="$biber_tmp_dir/biber"
    fi
fi
run_latex() {
    if ! pdflatex -interaction=nonstopmode -halt-on-error -file-line-error -output-directory="$output_dir" ClassicThesis.tex > "$output_dir/pdflatex-$1.log" 2>&1; then
        tail -n 25 "$output_dir/pdflatex-$1.log"
        return 1
    fi
}
run_latex 1
"$biber_command" --input-directory "$output_dir" --output-directory "$output_dir" ClassicThesis
run_latex 2
run_latex 3
printf 'Built %s/ClassicThesis.pdf\n' "$output_dir"
