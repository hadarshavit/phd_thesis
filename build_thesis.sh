#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
thesis_dir=$(cd .. && pwd)
bundle_dir=$(find "$thesis_dir/.cache/tectonic/bundles/data" -mindepth 1 -maxdepth 1 -type d | head -n 1)
export TEXINPUTS=".:$thesis_dir/.tools/tex-overrides//::$bundle_dir//"
export TFMFONTS=".::$bundle_dir//"
export VFFONTS=".::$bundle_dir//"
export T1FONTS=".::$bundle_dir//"

# TeX silently skips missing include files, so reject an incomplete checkout first.
python - <<'PY'
from pathlib import Path
import re
source = re.sub(r'(?m)(?<!\\)%.*', '', Path('ClassicThesis.tex').read_text())
missing = [name + '.tex' for name in re.findall(r'\\include\{([^}]+)\}', source)
           if not Path(name + '.tex').is_file()]
if missing:
    raise SystemExit('Missing chapter sources; push these files before building:\n' + '\n'.join(missing))
PY

output_dir="$thesis_dir/build"
mkdir -p "$output_dir/Chapters" "$output_dir/FrontBackmatter"
run_latex() {
    if ! pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$output_dir" ClassicThesis.tex > "$output_dir/pdflatex-$1.log" 2>&1; then
        tail -n 25 "$output_dir/pdflatex-$1.log"
        return 1
    fi
}
run_latex 1
"$thesis_dir/.tools/biber" --input-directory "$output_dir" --output-directory "$output_dir" ClassicThesis
run_latex 2
run_latex 3
printf 'Built %s/ClassicThesis.pdf\n' "$output_dir"
