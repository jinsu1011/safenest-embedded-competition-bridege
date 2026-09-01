# SafeNest 개발완료보고서 — 작업 인계 메모

최종 갱신 : 2026-08-30 (CO₂ 밀실 기준값 로컬라이징 가동)

---

## 0. 2026-08-30 변경

현재 Pi 런타임 `SAFENEST_RISK_V1` 을 보고서 정본 안전기준으로 올렸다.

- 정책 문서: `docs/09_SAFETY_CRITERIA_V1.md` (팀장에게 넘겨 P10 에이전트 입력으로 쓰는 브리핑. 법령·논문 URL·복붙 문장·금지 표현 포함)
- 슬라이드 원본: `generator/build.js` P3·P4·P6·P10·P14
- 엔진: `RaspberryPi/Runtime/risk/formula_v1.py` + `risk_formula_v1.json` (1.2.0, 절대 주의 1,500 ppm, 밀실 기준값 \(B\) + 상대 \(\Delta 700\))

구 V4 식(0.35/0.35, CAUTION, R≥60, 1,500 ppm=위험)은 보고서에 쓰지 않는다.

**맥에서 `generator/rebuild.sh` 로 PPTX·PDF를 다시 뽑아야 제출본이 갱신된다.** Pi에서는 Keynote export가 안 된다.

---

## 1. 지금 상태 한 줄 요약

`_최종수정프롬프트_v2.md` 의 배치 A~D 를 **전부 반영 완료**했고, 21장 전 페이지 육안 검수까지 마쳤다.
**남은 것은 P17 캡션 1줄 수정 하나뿐**이다. 그 외에는 제출 가능한 상태다.

---

## 2. 산출물 (파일명에서 `_DRAFT` 를 뗐다)

```
2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pptx   ← 최신
2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pdf    ← 최신
2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서_DRAFT.*  ← 구버전, 참고용
generator/build.js        편집 원본 (전면 재작성됨)
generator/build.js.bak    수정 전 원본 백업
generator/charts/make_charts.py   차트 3종 생성 스크립트 (신규)
previews/chart_co2.png · chart_mmwave.png · chart_victims.png
previews/pdf/p-01 ~ p-21.png
```

---

## 3. 이번에 한 일

### AI 문체 지문 제거 (v2 §5-3)
| 항목 | 전 | 후 |
|---|---:|---:|
| em dash `—` | 39 | **0** |
| 서술형(`~다`) 제목 | 20 | **0** (전부 `1.1 명사형` 번호 체계) |
| `라벨 — 설명문` 패턴 | 27 | **0** |
| 컬러 콜아웃 박스 | 15 | **4** (P6 규정 고지 / P9 표현 범위 / P16 테스트 수치 / P17 기대효과 범위) |
| 금지 패턴(`A가 아니라 B`, `핵심은` 등) | 다수 | **0** |
| 금지어(FastAPI·SQLite·WebSocket·팀번호·DRAFT 등) | — | **0** |

대단원을 `Ⅰ~Ⅶ` 로미숫자 + 소단원 `1.1 / 1.2 …` 로 바꿔 중간계획서 양식에 맞췄다.

### 레이아웃 (v2 §5-1, §5-2)
- `page()` 헬퍼 수정 : 제목 27→23 pt, 부제가 구분선을 뚫던 버그 해결, 콘텐츠 시작선 정리
- 본문 12 pt 이상 / 표 10.5~12 pt / 캡션 9~9.5 pt 로 상향
- 21장 전부 하단 넘침·겹침 제거

### 신규 콘텐츠
- **P3 시스템 구성도 신규 작도** (보고서 전체에 없던 최대 결손). 센서 4종 → ESP32 → TCP v1 → Pi 5 → 등급 4종 → 부저/LCD/Web. 화살표에 실제 인터페이스와 데이터 이름(`resp_rate_bpm`, `co2_ppm`, `thermal_max_c`, `pir_motion`, `valid{}`) 표기
- **P10 계산 예시 신규**. 정본 `ondevice_ai/risk/fallback.py` 를 **직접 실행해서** 얻은 값만 기재 :
  Thermal STALE → 유효 가중치 0.85 재정규화(0.412/0.412/0.176) → **R = 58.82 → CAUTION**, `system_health = DEGRADED`
- **P11 재구성** : 2단 구성으로 바꿔 `chart_mmwave.png`(미배치였던 것) 배치. ①CO₂ ②mmWave ③Thermal 로 검증 블록 분리
- 차트 3종 재생성 (제목의 em dash 제거, CO₂ 차트에 1,500 ppm 법정 기준선 추가, 도넛 신규)

### 사진 배치 (v2 §8)
| 사진 | 위치 |
|---|---|
| `hw_wiring_diagram.png` | P5 주력 (브레드보드 사진 대체) |
| `ui_lcd_6_failed.jpg` | P14 fail-closed 근거 |
| `hw_product_full_crop.jpg` + LCD 4종 | P16 |
| `ui_web.png` | P17 |
| CAD 2종 + `hw_product_emergency_crop.jpg` | P18 (설계 → 실물 대비 구도) |

하우징을 `설계 완료` → **`출력·조립 완료`** 로 상향. 단 `체결·발열 확인` 은 미검증 유지.
**LCD·웹 화면 캡션은 전부 "표시 계층 검증용 시나리오 입력이며 실센서 측정값이 아니다" 로 명시**했다 (§8-1).

### 조사 과제 (v2 §7)
- **① 선행 사례 → P15 반영 완료.** Vayyar Care(상용) / TI IWR6843(상용 부품) / arXiv 2403.05634(낙상 96.3 %). 공개 자료로 확인 못 한 항목은 `확인 불가` 로 두었고 출처를 각주에 남겼다
- **② 임계값 외부 근거 확보 → P10 반영 완료.**
  - CO₂ 1,500 ppm = **실내공기질 관리법 시행규칙 별표2** 기계환기 시설 유지기준과 동일한 값
  - 법정 적정공기(**산업안전보건기준에 관한 규칙 제618조**)는 CO₂ 1.5 %(15,000 ppm) 미만 → SafeNest 값이 훨씬 보수적인 조기경보 지점임을 명시
  - 위험도 30/60 과 CO₂ 2,000 ppm 은 `내부 실험 기준값` 이라고 P10 본문에 빨간 글씨로 못박음
- **③ BOM 원가 → 보류.** 8개 부품 전부의 출처 있는 단가를 확보하지 못했고 P17 공간도 부족. 근거 없는 원가표는 넣지 않았다 (v2 §7-③ 이 허용한 스킵)

### 정직성 유지 (건드리지 않은 것)
`4센서 통합 HIL = 미착수/미검증`, P15 마지막 행 `통합 실기기 검증 완료 = SafeNest만 ×`,
`mmWave v0.1.0 배포 차단`, `v0.2.0 = 합성 468샘플 한정`, `HUMAN_FALL = 눕기(LYING) 프록시`,
`테스트 57 passed / 2 failed (1,483개는 함수 개수)` — 전부 그대로 유지.

---

## 4. 내일 이어서 할 일

### (1) 남은 수정 1건 — 5분
`generator/build.js` 의 P17 블록에서 QR 설명문이 3줄로 넘쳐 각주와 겹친다. 아래로 교체하면 2줄로 맞는다.

```
찾기 : '현장 노드는 QR 로 공간을 식별한다. 관제 웹에 밀폐공간 A-01, 통학차량 B-02, 창고 C-03 코드가 생성되어 있다.'
교체 : '현장 노드는 QR 로 공간을 식별한다. 밀폐공간 A-01, 통학차량 B-02, 창고 C-03 코드가 생성되어 있다.'
```
수정 후 재빌드하고 `previews/pdf/p-18.png` 만 확인하면 된다.

### (2) 사용자가 채워야 하는 빈칸 2개
- **P3 소스코드 (GitHub) 밑줄** — 저장소 URL. 공식 명명규칙은 `2026ESWContest_free_가만있어도SANDI` 이므로 rename 여부부터 결정 필요
- **P3 시연동영상 (YouTube) 밑줄** — 아직 촬영 전. 예선 필수 제출물

두 칸 모두 지금은 **깨끗한 빈 밑줄**로 두었다(빨간 안내문구 없음). URL 이 정해지면 `build.js` 의 P3 블록에서 밑줄 위에 `hyperlink` 텍스트만 추가하면 된다.

### (3) 점수를 더 올리려면 (문서 밖 작업)
`10_FIRST_PLACE_GAP_ANALYSIS.md` 기준으로 아직 남은 것 :
1위 4센서 동시 수신 실기기 로그 → 2위 시연동영상 → 3위 통합 HIL → 5위 저장소 명명규칙.
1·3 이 끝나면 P11·P16 의 `미착수/미검증` 을 근거와 함께 갱신하면 된다.

---

## 5. 빌드 방법 (중요 — 함정 있음)

```bash
bash final-report/generator/rebuild.sh
```

**Keynote 관련 주의사항 :**
- 이 맥에 PowerPoint 가 없어 Keynote 로 PDF 변환한다. LibreOffice 도 없다
- 이전 실행에서 **Keynote 에 문서가 열린 채 남아 있으면 다음 export 가 AppleEvent 타임아웃(-1712)으로 실패**한다. `rebuild.sh` 에 `pkill -x Keynote` 를 넣어뒀지만, 실패하면 수동으로 `killall Keynote` 후 재시도할 것
- export 자체는 성공했는데 뒤의 `close`/`quit` 에서 타임아웃 나는 경우가 있다. 이때 **PDF 는 정상 생성되어 있으므로** PNG 렌더만 따로 돌리면 된다 :
  ```bash
  cd final-report/previews/pdf && rm -f p-*.png && pdftoppm -png -r 70 "../../2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pdf" p
  ```
- 한 번 빌드에 3~5분 걸린다

**검수는 반드시 PNG 를 눈으로 볼 것.** 텍스트 넘침이 자주 난다.

### 자가 점검 명령
```bash
cd final-report/generator
grep -c "—" build.js                                          # 0 이어야 함
grep -nE "page\([0-9]+, *'[^']*다'" build.js                   # 결과 없어야 함
grep -nE "이 아니라|가 아니라|핵심은|본질적으로|완벽하|혁신적" build.js   # 결과 없어야 함
grep -nE "FastAPI|SQLite|WebSocket|팀번호|DRAFT|1,483 tests" build.js  # 결과 없어야 함
```

---

## 6. 다른 노트북에서 이어서 하기

**아직 GitHub 에 올리지 않았다.** 이 맥의 `gh` 가 로그인되어 있지 않고, 무엇보다 결정할 게 하나 있어서다.

이 폴더에는 `09_HOSTILE_JUDGE_REVIEW.md`(적대적 심사 예상 70/100)와
`10_FIRST_PLACE_GAP_ANALYSIS.md`(약점 10건 목록) 같은 **내부 감사 문서**가 들어 있다.
`safenest-embedded-competition` 저장소가 **Public 이면 심사위원이 이걸 그대로 읽을 수 있다.**

그래서 올리기 전에 아래 중 하나를 골라야 한다.

| 안 | 내용 |
|---|---|
| **A** | 별도 **Private 저장소** 를 새로 만들어 폴더 전체를 올린다 (가장 안전) |
| **B** | 기존 저장소의 **새 브랜치** 에 올리되, 내부 감사 문서(`09_`, `10_`, `11_`, `HANDOFF.md`)는 제외 |
| **C** | 기존 저장소가 이미 Private 이면 그냥 폴더 전체를 새 디렉터리로 올린다 |

용량은 폴더 전체 약 18 MB 이고, `.HEIC` 원본과 `work/` 입력 패키지를 빼면 훨씬 가벼워진다.
GitHub 100 MB 제한에는 여유가 있다.

**필요한 준비** : 그 노트북/이 맥에서 `gh auth login` 한 번.
