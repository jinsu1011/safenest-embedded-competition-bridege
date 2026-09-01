#!/bin/bash
# SafeNest 보고서 재빌드 : PPTX 생성 → Keynote PDF export → 페이지 PNG 렌더
set -e
OUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PPTX="$OUT/2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pptx"
PDF="$OUT/2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pdf"

cd "$OUT/generator"
[ -d node_modules ] || npm install pptxgenjs
node build.js

rm -f "$PDF"; rm -rf "$OUT/previews/pdf"; mkdir -p "$OUT/previews/pdf"

# 이전 실행에서 남은 Keynote 문서가 export 를 막는다. 먼저 정리한다.
pkill -x Keynote 2>/dev/null || true
for i in 1 2 3 4 5 6 7 8 9 10; do pgrep -x Keynote >/dev/null || break; sleep 1; done
sleep 3
osascript <<OSA
with timeout of 900 seconds
    tell application "Keynote"
        activate
        set d to open (POSIX file "$PPTX")
        delay 6
        export d to file (POSIX file "$PDF") as PDF with properties {PDF image quality:Best}
        delay 4
        close d saving no
        quit
    end tell
end timeout
OSA
sleep 3
[ -f "$PDF" ] || { echo "ERROR: PDF export 실패"; exit 1; }
cd "$OUT/previews/pdf" && pdftoppm -png -r 70 "$PDF" p
echo "PPTX slides: $(python3 -c "import zipfile,re;print(len([n for n in zipfile.ZipFile('$PPTX').namelist() if re.match(r'ppt/slides/slide\d+\.xml$',n)]))")"
echo "PDF pages:   $(ls "$OUT/previews/pdf"/p-*.png | wc -l | tr -d ' ')"
echo "previews:    $OUT/previews/pdf/"
