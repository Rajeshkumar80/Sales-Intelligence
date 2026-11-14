#!/usr/bin/env bash
# One-off helper: download the two webfonts into public/fonts so the demo has no CDN dependency.
# Google serves a single variable file per family, so we keep one latin file each.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/public/fonts"
mkdir -p "$OUT"
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Pick the first latin block (U+0000-00FF) and emit "<url> <dest>".
first_latin() {
  curl -fsSL -A "$UA" "$1" | awk -v out="$OUT" -v prefix="$2" '
    /@font-face/ { block = "" }
    { block = block $0 "\n" }
    /unicode-range: U\+0000-00FF/ {
      if (!done && match(block, /https:\/\/[^)]*\.woff2/)) {
        print substr(block, RSTART, RLENGTH), out "/" prefix "-var.woff2"
        done = 1
      }
      block = ""
    }'
}

first_latin "https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600&display=swap" "instrument-sans" > "$OUT/urls.txt"
first_latin "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap" "jetbrains-mono" >> "$OUT/urls.txt"

while read -r url file; do
  curl -fsSL "$url" -o "$file"
  echo "saved $file ($(stat -c%s "$file") bytes)"
done < "$OUT/urls.txt"
rm -f "$OUT/urls.txt"
