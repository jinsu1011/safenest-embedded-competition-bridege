# final-report

제24회 임베디드SW경진대회(2026) 자유공모 부문 **개발완료보고서** 작업 폴더.

표지 1장 + 본문 20장 = 21슬라이드. PptxGenJS 로 생성하고 Keynote 로 PDF 변환한다.

---

## 산출물

| 파일 | 설명 |
|---|---|
| `2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pptx` | 제출용 PPTX (21슬라이드) |
| `2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pdf` | 제출용 PDF (21페이지) |
| `previews/pdf/p-01.png ~ p-21.png` | 페이지별 렌더 (레이아웃 검수용) |

**PPTX 를 직접 편집하지 마라.** 다음 재빌드 때 덮어써진다. 항상 `generator/build.js` 를 고친다.

---

## 폴더 구조

```
final-report/
├── HANDOFF.md              ★ 작업 인계 메모. 이어서 하려면 이것부터 읽는다
├── CONTINUE_PROMPT.md      ★ 다른 PC에서 Claude Code 로 이어서 할 때 붙여넣는 프롬프트
├── generator/
│   ├── build.js            ★ 슬라이드 편집 원본 (PptxGenJS). 모든 수정은 여기서
│   ├── rebuild.sh          PPTX 생성 → Keynote PDF export → PNG 렌더
│   ├── package.json
│   └── charts/make_charts.py   실측 차트 3종 생성 스크립트
├── assets/                 보고서에 삽입된 이미지 (배선도·완성품·LCD 6종·웹·CAD·QR)
├── previews/
│   ├── chart_co2.png       P11 삽입 (SCD40 실측)
│   ├── chart_mmwave.png    P11 삽입 (리플레이 정량)
│   ├── chart_victims.png   P1 삽입 (재해자 구성 도넛)
│   └── pdf/                페이지별 렌더
└── docs/                   근거·감사 문서 (수정 전 필독)
    ├── 00_SUBMISSION_REQUIREMENTS.md   공식 요구사항
    ├── 01_EVIDENCE_AUDIT.md            주장별 증거·등급
    ├── 02_REQUIREMENT_MATRIX.md        공식항목·심사항목 ↔ 페이지 대응
    ├── 03_CLAIM_EVIDENCE_LEDGER.md     강한 주장의 허용/금지 표현
    ├── 04_SOURCE_CONFLICT_AUDIT.md     ★ 자료 충돌 18건 해소 결과. 수정 전 필독
    ├── 05_ASSET_INDEX.md               이미지·데이터 목록
    ├── 06_SOURCES.md                   출처·데이터셋·라이선스
    ├── 07_MISSING_EVIDENCE_PRIORITY.md 결손 증거 우선순위
    ├── 08_PAGE_PLAN.md                 표지+20p 페이지 설계
    ├── 09_SAFETY_CRITERIA_V1.md        ★ 팀장·에이전트용 안전기준 브리핑 (P10 정본, 출처 포함)
    └── 11_FINAL_SUBMISSION_CHECKLIST.md 제출 체크리스트
```

---

## 빌드

```bash
cd final-report/generator
npm install          # 최초 1회 (pptxgenjs)
bash rebuild.sh
```

`rebuild.sh` 가 하는 일 : `node build.js` → Keynote 로 PDF export → `previews/pdf/` 에 21장 PNG 렌더.

### macOS 전제
PowerPoint·LibreOffice 없이 **Keynote** 로 변환한다. macOS 가 아니면 이 스크립트는 동작하지 않는다.

### 알려진 함정
- 이전 실행에서 **Keynote 에 문서가 열린 채 남아 있으면 다음 export 가 AppleEvent 타임아웃(-1712)으로 실패**한다. 실패하면 `killall Keynote` 후 재시도한다.
- export 는 성공했는데 뒤의 `close`/`quit` 에서 타임아웃 나는 경우가 있다. 이때 **PDF 는 정상 생성되어 있으므로** PNG 렌더만 따로 돌리면 된다:
  ```bash
  cd final-report/previews/pdf && rm -f p-*.png
  pdftoppm -png -r 70 "../../2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pdf" p
  ```
- 한 번 빌드에 3~5분 걸린다.

**수정 후에는 반드시 `previews/pdf/*.png` 를 눈으로 확인한다.** 텍스트 넘침이 자주 난다.

---

## 편집 규칙

`build.js` 는 `/* ====== P1 ====== */` ~ `P20` 주석으로 슬라이드가 구분되어 있다.
공통 헬퍼: `page(n, title, sub)` 헤더 · `box()` · `badge()` 증거배지 · `hdr()` 표 헤더 · `sub()` 소제목 · `note()` 각주 · `cap()` 캡션.

### 지켜야 할 것
1. **콘텐츠 20페이지 초과 금지.** 표지 제외 20p 까지만 평가된다. 추가하려면 무언가를 빼야 한다.
2. **분량 배분 유지** : 개발개요 3p(P1–3) / 환경·프로그램·장애요인 10p(P4–13) / 차별성·파급력 5p(P14–18) / 일정·업무분장 2p(P19–20)
3. **날조 금지.** 정확도·지연·오탐률·가용성·시장규모·매출·테스트 결과·사진·팀 기여를 지어내지 않는다. 증거가 없으면 `미검증` / `[추가 검증 필요]` 로 쓴다.
4. **문체** : 제목은 전부 명사형 + 번호 체계(`1.1`). em dash(`—`) 금지. `A가 아니라 B` 같은 패턴 금지.

### 자가 점검
```bash
cd final-report/generator
grep -c "—" build.js                                                    # 0
grep -nE "page\([0-9]+, *'[^']*다'" build.js                             # 결과 없음
grep -nE "이 아니라|가 아니라|핵심은|본질적으로|완벽하|혁신적" build.js      # 결과 없음
grep -nE "FastAPI|SQLite|WebSocket|팀번호|DRAFT|1,483 tests" build.js     # 결과 없음
```
네 줄 모두 통과해야 한다.

---

## 이 폴더에 없는 것

- **`node_modules/`** — `npm install` 로 재생성한다.
- **`work/` 입력 패키지 (약 341 MB)** — 검증된 원본 증거 묶음. 그중 279 MB 는 이 저장소 자체의 스냅샷 복사본이라 저장소 안에 다시 넣지 않았다. `generator/charts/make_charts.py` 는 이 경로를 읽으므로 **차트를 재생성하려면 원본 패키지가 필요**하다. 다만 생성된 차트 PNG 3종이 이미 포함되어 있어 **보고서 빌드에는 필요 없다.**
- **`.HEIC` 사진 원본** — JPG 변환본만 포함했다. `build.js` 는 HEIC 를 참조하지 않는다.
