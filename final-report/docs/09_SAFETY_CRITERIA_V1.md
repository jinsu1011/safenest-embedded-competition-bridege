# SafeNest 안전기준 브리핑 v1.2.0

| 항목 | 내용 |
|---|---|
| 날짜 | 2026-08-30 |
| 대상 | 팀장. 이 파일을 에이전트에 그대로 넘겨 개발완료보고서 P10(위험도·안전기준)을 쓰게 하면 된다 |
| 정본 엔진 | Raspberry Pi `SAFENEST_RISK_V1` |
| 코드 | `RaspberryPi/Runtime/risk/formula_v1.py` |
| 숫자 | `RaspberryPi/Runtime/risk/risk_formula_v1.json` **1.2.0** |
| 검증 | `test_risk_formula_v1.py` + `test_co2_baseline_lock.py` (2026-08-30 PASS) |
| 출처 확인일 | 2026-08-30 (웹 원문 대조) |

이 문서는 **인증·의료·산업안전기준 준수를 주장하지 않는다.** 아래 법령·논문 숫자는 프로토타입 경보 지점을 고른 근거다. SafeNest가 그 기준을 만족한다는 뜻이 아니다.

슬라이드에 쓸 문장은 **§11 복붙 문장**만 사용한다. 그 밖의 과장 표현은 §12 금지 목록을 따른다.

---

## 에이전트에게 시킬 일 (팀장 붙여넣기용)

1. 개발완료보고서 **P10**의 위험도 식·가중치·등급·채널 플로어·계산 예시를 이 문서 §4·§5·§11과 일치시킬 것.
2. 각주에 넣을 출처는 **§2·§3 표의 URL**을 그대로 쓸 것. 추측으로 조문·DOI를 만들지 말 것.
3. 별표2는 **기본 1,000 ppm / 비고 예외 1,500 ppm**으로 정확히 쓸 것. 1,500만 “별표2 유지기준”이라고 단정하지 말 것(구 08.24 보고서의 오류).
4. **상대 기준 \(B\), \(\Delta 700\)** 은 Pi에서 **가동 중**이다. occupancy(C-B6)와 섞어 쓰지 말 것. \(B\)는 밀실 공기 기준값이고 occupancy는 사람 유무다.
5. occupancy(C-B6)는 위험 점수에 넣지 않는다.
6. 구 V4 (`0.35/0.35`, `CAUTION`, `R\ge60`, 1,500=위험, 2,000=EMERGENCY)는 폐기. 유승하 표도 폐기.
7. 열화상은 눕기 자세 프록시. mmWave 신경망은 관측 전용. “낙상 감지 완료”, “임상 무호흡” 금지.
8. 스타일: 엠대시(—) 금지. “A가 아니라 B” 금지. FastAPI·SQLite·WebSocket은 정본에 없음.

---

## 0. 한 장 요약 — CO₂ 1차 확정

| 항목 | 1차 확정값 | 지금 엔진 | 근거 | 보고서에 쓸 때 |
|---|---|---|---|---|
| 밀실 기준값 \(B\) | 부팅·갭 이후 약 3분, 측정 이벤트의 중앙값 | **가동** `CO2BaselineLock` | Persily 2022 (P1) | 밀실 공기 로컬라이징 |
| 상대 주의 \(\Delta=\mathrm{ppm}-B\) | \(\Delta\ge +700\) ppm, **양수만**. 해제 \(+500\) | **가동** 플로어 `co2_relative_warning` | ASHRAE 62.1 informative (A1) | 요구사항이 아닌 환기 지표 |
| 절대 주의 천장 | **\(\ge 1{,}500\) ppm** → `co2_warning` | **가동** | 별표2 비고·학교보건 기계환기 예외 (K2, K3) | 주의. 위험이 아님 |
| 절대 주의 상한 | **\(\ge 2{,}500\) ppm** → `co2_danger` | **가동** | Satish 2012 (P3) | 단독 사이렌 아님 |
| 즉시 위험 | **\(\ge 5{,}000\) ppm** | **가동** | OSHA PEL / NIOSH REL / ACGIH TLV 8h TWA (U1) | 8h 평균을 순간 비상으로 당겨 쓴 팀 정책이라고 명시 |
| 상승 주의 / 급상승 | **15 / 50 ppm/min** | **가동** | Cenci 2020 (P4) | 기울기 보너스 |
| 산안 적정공기 | 15,000 ppm (1.5 %) | 참고만. 트립 아님 | 제618조 (K4). **구 보고서에 이미 있음** | 우리 5,000이 이보다 낮다는 비교만 |
| occupancy 모델 | 안전 점수 제외 | **가동** | C-B6 `risk_semantic: NONE` (P5) | **사람** 로컬라이징. 위험 가중치 아님 |

필드 idle **약 1,184 ppm** → 1,500 미만이므로 **절대 주의가 아니다.**
호기 실측 최고 **1,493 ppm** (2026-08-12) → 1,500 직전.

별표2 **기본 1,000 ppm**은 자연환기 다중이용시설 값이다. 밀폐 노드의 절대 트립으로 쓰면 필드 idle이 상시 주의가 된다. 그래서 1차로 **쓰지 않는다.** \(B\)가 잠기면 \(B+700\)이 1,000보다 먼저 뜰 수 있다.

JSON 키 (엔진이 읽는 값):

```
warning_ppm = 1500
danger_ppm = 2500          # WARNING 플로어. 단독 DANGER 아님
immediate_danger_ppm = 5000
slope_warning_ppm_per_min = 15
slope_danger_ppm_per_min = 50
baseline_delta_warning_ppm = 700
baseline_delta_clear_ppm = 500
baseline_lock_seconds = 180
baseline_minimum_samples = 3
baseline_runtime_status = ACTIVE
```

---

## 1. 구 보고서(08.24)에 이미 있던 출처 vs 이번 수정

08.24 개발완료보고서 P10에 **이미 적혀 있던 것:**

| 구 보고서 문장 | 원문 대조 (2026-08-30) | 조치 |
|---|---|---|
| 1,500 ppm = 별표2 기계환기 유지기준과 같은 값 | **부분만 맞음.** 별표2 **기본은 1,000 ppm.** 1,500은 “자연환기가 불가능하여 자연환기설비 또는 기계환기설비를 이용하는 경우”의 **비고 예외** | 보고서에 기본/예외를 둘 다 적을 것 |
| 산안규칙 제618조 적정공기 CO₂ 1.5 % = 15,000 ppm | **원문과 일치** | 유지 |
| 위험도 30/60, CO₂ 2,000 ppm은 팀 실험값 | 30/60은 구 V4. 2,000 ppm EMERGENCY는 법령·OSHA에 없음 | **폐기.** 현재는 30/65, 비상 5,000 |

유승하 표 (NORMAL 400–600 / CAUTION >1,000 / WARNING ≥1,500 / EMERGENCY ≥2,000)와 구 스냅샷 `co2_ppm > 1500` → 성분 1.0 은 **현재 정본이 아니다.**

---

## 2. 공식 출처 (웹 원문 확인, 2026-08-30)

에이전트는 “문서가 실제로 말하는 것” 열만 인용한다. 우리 사용 열을 원문인 것처럼 쓰지 않는다.

### 2.1 한국 법령

| ID | 숫자 | 문서가 실제로 말하는 것 | 원문 | 우리 사용 |
|---|---|---|---|---|
| **K1** | **1,000 ppm 이하** | 다중이용시설 실내공기질 **유지기준**. 지하역사·대합실·영화상영관·학원 등 | 「실내공기질 관리법」 제5조, 「같은 법 시행규칙」 제3조·[별표 2] (개정 2024.12.23.). 생활법령정보 해설 기준일 2026-07-15. https://www.easylaw.go.kr/CSP/CnpClsMain.laf?ccfNo=4&cciNo=1&cnpClsNo=2&csmSeq=1827 | 밀폐 노드 **절대 트립으로 쓰지 않음** |
| **K2** | **1,500 ppm 이하** | 별표2 비고: 도서관·영화상영관·학원·인터넷컴퓨터게임시설 중 **자연환기가 불가능하여 자연환기설비 또는 기계환기설비를 이용하는 경우** | 같은 별표2 비고. 법제처 별표 파일 https://www.law.go.kr/LSW/flDownload.do?bylClsCd=110201&flSeq=157776827&gubun= | **1차 절대 주의 천장 1,500.** 구 보고서가 쓰던 1,500의 정확한 의미 |
| **K3** | **1,000 / 1,500 ppm** | 학교 교사·급식시설 유지기준 1,000. **기계환기장치가 주된 환기이면 1,500** | 「학교보건법」 제4조, 「학교보건법 시행규칙」 제3조 [별표 4의2]. https://easylaw.go.kr/CSP/CnpClsMainBtr.laf?ccfNo=4&cciNo=3&cnpClsNo=2&csmSeq=1394&popMenu=ov | K2와 같은 1,500 예외를 교차 확인 |
| **K4** | **CO₂ 1.5 % 미만** = 15,000 ppm | 밀폐공간 장의 **“적정공기” 정의**. 산소 18 % 이상 23.5 % 미만, CO 30 ppm 미만, H₂S 10 ppm 미만과 함께 | 「산업안전보건기준에 관한 규칙」 제618조 제3호. 시행 2026.3.2. 고용노동부령 제450호. https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1016497817 | 구 보고서와 동일. **트립하지 않음.** 5,000 비상이 이보다 낮다는 비교만 |

**easylaw 별표2에서 직접 확인한 문장 (K1·K2):**

> 가. 지하역사, … 영화상영관, 학원, … → 이산화탄소 **1,000 이하** (ppm)
>
> ※ 도서관, 영화상영관, 학원, 인터넷컴퓨터게임시설제공업 영업시설 중 자연환기가 불가능하여 자연환기설비 또는 기계환기설비를 이용하는 경우에는 이산화탄소의 기준을 **1,500ppm 이하**로 유지해야 합니다.

**제618조 제3호 원문 (K4):**

> “적정공기”란 산소농도의 범위가 18퍼센트 이상 23.5퍼센트 미만, 이산화탄소의 농도가 1.5퍼센트 미만, 일산화탄소의 농도가 30피피엠 미만, 황화수소의 농도가 10피피엠 미만인 수준의 공기를 말한다.

### 2.2 작업장 노출 한계 (미국)

| ID | 숫자 | 문서가 실제로 말하는 것 | 원문 | 우리 사용 |
|---|---|---|---|---|
| **U1** | **5,000 ppm** 8h TWA | 작업장 **시간가중 평균** 노출 한계. 순간 천장값이 아님 | OSHA Chemical Data 183 (갱신 2024-05-23) PEL-TWA 5000 ppm (9000 mg/m³). https://www.osha.gov/chemicaldata/183 · NIOSH Pocket Guide REL-TWA 동일. https://www.cdc.gov/niosh/npg/npgd0103.html · ACGIH TLV–TWA 5000 ppm. https://www.acgih.org/carbon-dioxide/ | **즉시 위험 비상.** 8h 평균을 순간 상한으로 당겨 쓴 팀 정책이라고 쓸 것 |
| **U2** | **30,000 ppm** 15 min STEL | 단기 노출 한계 | OSHA: NIOSH REL-STEL 30,000 ppm. ACGIH TLV–STEL 30,000 ppm. 같은 URL | 참고. 트립 아님 |
| **U3** | **40,000 ppm** IDLH | NIOSH Immediately Dangerous to Life or Health. OSHA 183이 NIOSH IDLH로 기재 | https://www.osha.gov/chemicaldata/183 | 참고. 트립 아님 |

### 2.3 ASHRAE (환기 지표. 건강 한도 아님)

| ID | 숫자 | 문서가 실제로 말하는 것 | 원문 | 우리 사용 |
|---|---|---|---|---|
| **A1** | 실내−실외 **약 700 ppm** | 사람 생체냄새 기준으로 약 15 cfm/인 환기에 해당. **요구사항이 아님.** IC 62-2001-06: 이 값을 넘겨도 표준 준수 가능 | ASHRAE FAQ 35 https://www.ashrae.org/File%20Library/Technical%20Resources/Technical%20FAQs/TC-04.03-FAQ-35.pdf · Trane Engineers Newsletter 31-3 https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/education-training/engineers-newsletters/airside-design/adm_apn004_en.pdf · IC 62-2001-06 https://www.ashrae.org/File%20Library/Technical%20Resources/Standards%20and%20Guidelines/Standards%20Intepretations/IC_62-2001-06.pdf | 상대 주의 \(\Delta\ge 700\). 실외 대신 밀실 잠금값 \(B\)를 쓴다. **가동 중** |
| **A2** | 절대 1,000 ppm은 ASHRAE 한도가 **아님** | 1989판의 절대 1,000 문장은 Addendum 62f(1999) 이후 실내−실외 700 관찰로 고침 | 위 Trane 31-3. ASHRAE Position Document on Indoor Carbon Dioxide (2022). NIST 배경 https://www.nist.gov/publications/development-and-application-indoor-carbon-dioxide-metric-0 | “ASHRAE 1,000 ppm 한도”라는 문장 금지 |

---

## 3. 논문·기술문헌

| ID | 문헌 | 핵심 수치·주장 | 우리 사용 | 보고서에 쓰지 말 것 |
|---|---|---|---|---|
| **P1** | Persily A. (2022). Development and application of an indoor carbon dioxide metric. *Indoor Air*. https://doi.org/10.1111/ina.13059 · NIST https://www.nist.gov/publications/development-and-application-indoor-carbon-dioxide-metric-0 | 모든 공간에 1,000 ppm 하나로는 환기 지표가 부적절. **공간별 CO₂ 지표** | 밀실 초기값 \(B\) 잠금의 학술 근거 | “Persily가 1,500을 한도로 정했다” |
| **P2** | Persily, NIST TN 2213 (2022). https://doi.org/10.6028/nist.tn.2213 | QICO2 계산 도구 | P1 보조 | — |
| **P3** | Satish U. et al. (2012). *Environ Health Perspect* 120:1671–1677. https://doi.org/10.1289/ehp.1104789 · PMC https://pmc.ncbi.nlm.nih.gov/articles/PMC3548274/ | 사무실 챔버 n=22. 600 / **1,000** / **2,500** ppm. 1,000에서 의사결정 9개 척도 중 **6개** 유의 저하. 2,500에서 **7개** 크게 저하. 저자: **확인(confirmation)이 필요하다** | **2,500**을 단독 DANGER가 아닌 주의 상한으로 두는 근거 | 산업 노출 한계처럼 인용. “인지 장애가 입증됐다” 단정 |
| **P4** | Cenci G. et al. (2020). Occupancy estimation in educational buildings. https://pmc.ncbi.nlm.nih.gov/articles/PMC7411428/ | 교실 CO₂ 상승 0.11–0.75 ppm/s ≈ **6–45 ppm/min**. 평균 약 **25–28 ppm/min**. 피크 **약 50 ppm/min** | 기울기 **15** (조기) / **50** (피크) | “교실 평균을 위험 기준으로 썼다” |
| **P5** | Cali D. et al. (2015). *Building and Environment*. https://doi.org/10.1016/j.buildenv.2014.12.008 | CO₂와 \(dC/dt\)로 재실 추정 | occupancy는 **별도 모델**. 위험 점수 제외 | occupancy 출력을 위험 가중치로 설명 |
| **P6** | ASHRAE 62-1989 → Addendum 62f (1999) | 절대 1,000 문장 삭제, 실내−실외 700 | 상대 \(\Delta 700\) | “ASHRAE가 700을 의무화했다” |
| **P7** | Chourpiliadis C, Bhardwaj A. Physiology, Respiratory Rate. *StatPearls*. https://www.ncbi.nlm.nih.gov/books/NBK537306/ | 안정 시 성인 호흡 **12–20 /min** | mmWave 규칙 대역의 **임상 상한 참고**. 우리는 필드 벤더 스칼라 때문에 **10–24**로 넓힘 (§7) | “10–24가 임상 정상이다” |
| **P8** | American Lung Association. 안정 시 성인 12–20 /min. 12 미만 또는 **25 초과**는 우려. https://www.lung.org/blog/respiratory-rate-vital-signs | 상한 25 근처 | 24 rpm 상한의 인접 근거 | 임상 진단 |

Satish 원문 결론 문장 (P3, 보고서에 필요하면 이 범위만):

> At 1,000 ppm CO2, compared with 600 ppm, performance was significantly diminished on six of nine metrics … At 2,500 ppm … seven of nine … Confirmation of these findings is needed.

---

## 4. 융합 식 (P10 정본)

\[
R = 100 \times \frac{\sum w_i s_i}{\sum w_i}\quad (i=\text{가용 채널만})
\]

구현: `formula_v1.py`. 가중치 합 = 1.0.

| 채널 | 가중치 | 이유 |
|---|---:|---|
| CO₂ | 0.30 | 지금 가장 신뢰할 수 있는 연속 스칼라 |
| 열화상 | 0.30 | 활성 모델 있으나 자세 프록시만 허용 |
| mmWave | 0.25 | 신경망은 관측 전용. 호흡수 규칙만 점수 |
| PIR | 0.15 | 재실 보강. 단독 위험 선언 금지 |

구 V4 가중치 0.35 / 0.35 / 0.15 / 0.15 는 **쓰지 않는다.**

| 표시 | 코드 | 조건 |
|---|---|---|
| 정상 | `NORMAL` | \(R < 30\) 이고 플로어·비상 없음, 유효 가중치 \(\ge 0.5\) |
| 주의 | `WARNING` | \(30 \le R < 65\) **또는** 주의 플로어 |
| 위험 | `DANGER` | \(R \ge 65\) **또는** 즉시 비상 |
| 판단 보류 | `INDETERMINATE` | 유효 가중치 \(< 0.5\) 인데 정상으로 가려 할 때 |
| 미산출 | `None` | 전 채널 무효. `system_health=FAILED` |

가중합만 쓰면 한 채널의 심한 위험이 희석된다. **에스컬레이션 플로어**가 점수보다 등급을 올릴 수 있다. 점수가 1.0이라고 전부 즉시 위험은 아니다.

점수 30 / 65 는 **팀 프로토타입 구간**이다. 법령 숫자가 아니다.

---

## 5. 채널 정책 (지금 엔진)

### 5.1 CO₂

Occupancy 모델 C-B6은 `risk_semantic: NONE` 이라 안전 점수에 넣지 않는다. ppm 곡선 + 기울기 + 절대 플로어만 넣는다.

ppm → 점수 곡선 (JSON `curve_ppm_to_score`, 선형 보간):

| ppm | 점수 |
|---:|---:|
| 600 | 0.00 |
| 1,000 | 0.15 |
| 2,000 | 0.50 |
| 5,000 | 0.90 |
| 10,000 | 1.00 |

곡선상의 1,000은 **점수 앵커**일 뿐, 주의 플로어가 아니다. 주의 플로어는 `warning_ppm = 1500`.

| 조건 | 동작 | 비상 |
|---|---|---|
| \(\ge 1{,}500\) ppm | 플로어 `co2_warning` → 주의. 사유 `HIGH_CO2_WARNING` | 없음 |
| \(\ge 2{,}500\) ppm | 플로어 `co2_danger` → 주의 유지. 사유 `HIGH_CO2_DANGER` | 없음 |
| \(\ge 5{,}000\) ppm | 플로어 `co2_immediate_danger` → 위험. 사유 `CO2_IMMEDIATE_DANGER` | **있음** |
| 잠긴 \(B\) 대비 \(\Delta\ge +700\) | 플로어 `co2_relative_warning` → 주의. 사유 `CO2_RELATIVE_RISE` | 없음 |
| 상승 \(\ge 15\) ppm/min | 점수 +0.10, 사유 `FAST_CO2_RISE` | 없음 |
| 상승 \(\ge 50\) ppm/min | 점수 +0.25, 플로어 `co2_fast_rise` | 없음 |

기울기는 AI 파이프라인 캐노니컬 슬로프(`CO2_SLOPE_FEATURE_PROFILE_001`)를 우선하고, 없으면 로컬 엔드포인트.

**밀실 공기 로컬라이징 (가동 중, Pi only):**

두 가지를 섞지 않는다.

| 신호 | 하는 일 | 위험 점수 |
|---|---|---|
| `CO2BaselineLock` | 부팅·90 s 갭 이후 측정 이벤트 3분 중앙값으로 \(B\)를 잠근다. \(\Delta=\max(0,\mathrm{ppm}-B)\) | \(\Delta\ge 700\) 이면 주의 플로어. 해제는 500 |
| C-B6 occupancy | VACANT / OCCUPIED | **넣지 않음** (`risk_semantic: NONE`) |

\(B\)가 잠기기 전 상태는 `CO2_LOCALIZING` 이다. ESP32는 raw ppm과 `measurement_event_id`만 보낸다. \(B\)보다 낮아지는 방향은 환기 개선이며 위험이 아니다.

### 5.2 열화상

활성 모델: `thermal_public_sdt_fp32_active`. `safety_authority: false`. `proxy_emergency_allowed: false`.

| 출력 | 점수 | 화면 | 비상 |
|---|---:|---|---|
| `NOT_HUMAN` / `HUMAN_NORMAL` | 0.0 | 가중합만 | 없음 |
| `HUMAN_FALL_PROXY` | 0.4 | 점수 기여 | **없음** |
| `HUMAN_FALL` 신뢰도 \(\ge 0.8\) | 1.0 | 위험 | 있음. **현재 활성 모델은 이 클래스를 내지 않음** |

`HUMAN_FALL`은 시간축 낙상 사건이 아니라 **눕기(LYING) 정적 자세 프록시**다. 실기기 E2E는 열화상 채널에 한한다 (p50 162.70 ms / p95 173.90 ms, 유효 135/138).

### 5.3 mmWave

신경망 기본 `neural_trust: OBSERVE_ONLY`. 이유: `MMWAVE_M_N9_FULL_INT8_V1` 은 `DEVICE_VALIDATED: NO`, Pi 스모크 미실시. 20260817 캡처에서 호흡 대역 전력 82 %·20 rpm 피크인데도 APNEA-proxy 고신뢰가 나옴.

| 출력 | 점수 | 화면 | 비상 |
|---|---|---|---|
| 신경망 클래스 (OBSERVE_ONLY) | 점수에 안 넣음 | 기록만 | 없음 |
| 미검증 `APNEA-proxy` 2회 연속 (`TRUSTED`일 때만) | 주의 상한 | 주의 | **없음** |
| 호흡수 10–24 rpm 이탈 3회 | 0.50 → 지속 시 0.75 | 점수 상승 | 없음 |
| 하드웨어 확인 `apnea_verified` | DANGER | 위험 | **있음** |

호흡수 우선순위: 스펙트럼 캐노니컬 창 → 벤더 `MR60_BREATH_RATE_RAW`.

정상 대역 **10–24 rpm**: 임상 관행은 **12–20** (P7, P8). 구 V4는 12–20을 써서 20260817 캡처 평균 9.63 rpm이 상시 이상으로 집계됐다. 그래서 대역을 넓히고 3회 지속을 넣었다. 임상 정상 범위라고 쓰지 말 것.

### 5.4 PIR

재실이 확인되지 않으면 무움직임을 **0점이 아니라 비가용**으로 둔다. 재실 확인 후 유예 30 s, **180 s** 무움직임은 주의 플로어 `pir_long_no_motion`. 구 V4는 15 s에 곧바로 1.0이었다.

---

## 6. 필드·실측 숫자 (보고서에 그대로 쓸 수 있는 것만)

| 측정 | 값 | 안전기준과의 관계 |
|---|---|---|
| 20260817 필드 idle CO₂ | 약 **1,184 ppm** | 1,500 미만 → 절대 주의 아님. 곡선 점수 약 0.20 |
| 2026-08-12 호기 세션 최고 | **1,493 ppm**, 종료 634 ppm | 1,500 직전. 위험 아님 |
| 같은 날 재측정 baseline | 300/300, 결측 0 % | 센서 경로 검증. 안전기준 숫자가 아님 |
| 최초 baseline | 277/300, 결측 7.67 % **FAIL로 보존** | 실패를 지운 기록이 아님 |
| 20260817 mmWave `respiration_rate_bpm` | min 0 / mean **9.63** / max 27 | 10–24 확장의 필드 이유 |
| P10 계산 예시 (엔진 실행) | 16 rpm · 1,500 ppm · 움직임 · `HUMAN_NORMAL` | \(R=9.75\) 정상, 플로어 → **주의**, 비상 아님 |

검증 테스트:

- `test_indoor_air_quality_anchor_raises_warning_even_when_r_is_low` — 1,500 ppm, \(R=9.75\), `co2_warning`
- `test_table2_default_1000_ppm_is_not_the_live_warning_floor` — 1,000은 플로어 없음
- `test_field_capture_level_co2_is_a_low_score` — 1,184는 플로어 없음

---

## 7. 보고서용 계산 예시 (엔진 직접 실행값)

입력: 호흡 16 rpm · CO₂ 1,500 ppm · 움직임 있음 · 열화상 `HUMAN_NORMAL`.

성분: mmWave 0.00, CO₂ 0.325, PIR 0.00, Thermal 0.00.

\[
R = 100 \times (0.25\cdot 0 + 0.30\cdot 0.325 + 0.15\cdot 0 + 0.30\cdot 0) = 9.75
\]

점수 등급 **정상**. 플로어 `co2_warning` → 표시 **주의**. 비상 아님. mmWave 신경망이 관측 전용이라 `system_health = DEGRADED` 가 될 수 있다.

---

## 8. 왜 이 숫자인가 (결정 로그)

| 후보 | 채택 여부 | 이유 |
|---|---|---|
| 절대 주의 = 1,000 (별표2 기본, ASHRAE 오인용) | **기각** | 필드 1,184가 상시 주의. ASHRAE도 1,000을 한도로 두지 않음 (A2) |
| 절대 주의 = 1,500 (별표2 비고) | **채택** | 기계환기·밀폐에 해당하는 국내 유지기준 예외. 구 보고서가 이미 쓰던 숫자이되 의미를 바로잡음 |
| 상대 \(\Delta 700\) | **채택, 가동** | Persily·ASHRAE. `CO2BaselineLock` + 플로어 `co2_relative_warning` |
| 2,000 EMERGENCY (유승하) | **기각** | 법령·OSHA 근거 없음 |
| 2,500 = 단독 DANGER | **기각** | Satish는 인지 실험. 사람 상태 평온한데 가스만으로 사이렌을 울리지 않음 |
| 5,000 = 즉시 위험 | **채택** | OSHA/NIOSH/ACGIH 8h TWA와 **같은 숫자**. 순간 적용은 팀 정책 |
| 15,000 = 트립 | **기각** | 제618조 적정공기. 너무 늦음. 비교 인용만 |
| 기울기 15/50 | **유지** | Cenci 교실 하한~피크. 기존 엔진과 동일 |
| 호흡 12–20 | **기각** | 필드 평균 9.63이 상시 이상 |
| 호흡 10–24 | **채택** | 필드 + 임상 12–20을 감싼 팀 대역. 임상 정상이라고 쓰지 않음 |

---

## 9. 코드·파일 지도 (에이전트가 경로를 틀리지 않게)

| 역할 | 경로 | 비고 |
|---|---|---|
| 지금 도는 엔진 | `RaspberryPi/Runtime/risk/formula_v1.py` | 정본 |
| 지금 도는 숫자 | `RaspberryPi/Runtime/risk/risk_formula_v1.json` 1.2.0 | 정본 |
| 테스트 | `RaspberryPi/Runtime/tests/test_risk_formula_v1.py` | 26 tests |
| CO₂ 슬로프 창 | `RaspberryPi/Runtime/ai/co2_canonical_runtime.py` `CO2SlopeWindowBuilder` | 150 s, occupancy용 |
| CO₂ 밀실 기준값 | 같은 파일 `CO2BaselineLock` | 180 s 중앙값, 양수 \(\Delta\)만 |
| 진입점 | `RaspberryPi/Runtime/deployment/run_pi.sh` → `backend/run_backend.py` | |
| **돌지 않음** | `RaspberryPi/Runtime/risk/engine.py` (구 V4) | 인용 금지 |
| **돌지 않음** | `Ondevice_AI/risk/*`, `integrated_node/safenest_risk_engine.py` | 인용 금지 |
| **돌지 않음** | `ondevice_ai/risk/fallback.py` | 구 보고서가 잘못 인용하던 파일 |
| 슬라이드 원본 | `final-report/generator/build.js` P10 | PPTX 직접 편집 금지 |
| 이 브리핑 | `final-report/docs/09_SAFETY_CRITERIA_V1.md` | |

---

## 10. 기존 충돌 표 (C12 요약)

| 출처 | 내용 | 처리 |
|---|---|---|
| 유승하 표 | EMERGENCY ≥ 2,000 | 폐기 |
| 구 V4 / fallback.py | 가중 0.35/0.35, CAUTION, \(R\ge 60\), 1,500=위험 | 폐기 |
| 08.24 P10 | 별표2 = 1,500만 기재 | 기본 1,000 + 비고 1,500으로 수정 |
| 현재 JSON 1.2.0 | 주의 1,500 / 상대 \(B\)+700 / 상한 2,500(주의) / 비상 5,000 | **채택** |

---

## 11. 보고서에 복붙할 문장

**식**

> 위험도 \(R\) 은 가용 채널만으로 가중 평균한다. \(R = 100 \times (0.25\cdot\mathrm{mmWave} + 0.30\cdot\mathrm{CO_2} + 0.15\cdot\mathrm{PIR} + 0.30\cdot\mathrm{Thermal})\). 정상은 \(R<30\), 주의는 \(30\le R<65\), 위험은 \(R\ge 65\) 이다. 한 채널의 심한 위험이 희석되지 않도록 채널 플로어가 점수보다 등급을 올릴 수 있다.

**CO₂**

> CO₂ 절대 주의 천장은 1,500 ppm 이다. 이는 「실내공기질 관리법 시행규칙」 별표2의 **기본값 1,000 ppm**이 아니라, 자연환기가 불가능하여 기계환기를 쓰는 시설에 적용되는 **비고 예외 1,500 ppm**과 같은 값이다. 학교보건법 시행규칙 별표 4의2도 기계환기가 주된 환기이면 1,500 ppm 이다. 1,500 ppm 은 주의 구간이며 위험 선언값이 아니다. 2,500 ppm 도 주의 플로어로 유지하여, 사람 상태가 평온할 때 가스 채널 단독으로 사이렌을 울리지 않는다. 즉시 위험은 5,000 ppm 이며, OSHA·NIOSH·ACGIH의 8시간 TWA와 같은 숫자를 순간 비상으로 당겨 쓴 팀 프로토타입 정책이다. 「산업안전보건기준에 관한 규칙」 제618조 적정공기의 이산화탄소 1.5 %(15,000 ppm)보다 낮다. 본 시스템은 위 법령·권고의 인증 준수를 주장하지 않는다.

**계산 예시**

> 호흡 16 rpm, CO₂ 1,500 ppm, 움직임 있음, 열화상 HUMAN_NORMAL 이면 \(R=9.75\) 로 점수 등급은 정상이나, 플로어 `co2_warning` 으로 주의가 표시된다. 비상은 아니다.

**로컬라이징**

> CO₂ 로컬라이징은 두 층이다. 밀실 공기 기준값 \(B\) 는 부팅 또는 통신 갭 이후 약 3분 동안의 측정 이벤트 중앙값으로 잠근다. \(B\) 보다 700 ppm 이상 오른 경우만 주의 플로어를 올리고, \(B\) 아래로 떨어지는 것은 환기 개선으로 본다. 사람 occupancy 모델(C-B6)은 위험 점수에 넣지 않는다.

**열화상 / mmWave (한 줄)**

> 열화상 HUMAN_FALL_PROXY 는 점수 0.4 이며 비상을 울리지 않는다. 현재 모델은 눕기 자세 프록시만 낸다. mmWave 신경망은 관측 전용이며, 하드웨어가 확인한 apnea 만 즉시 위험이다.

**fail-closed**

> 전 채널이 무효이면 위험도를 산출하지 않는다. 유효 가중치가 0.5 미만인데 정상으로 가려 하면 INDETERMINATE 를 낸다. NORMAL 과 UNKNOWN 을 같은 화면으로 두지 않는다.

---

## 12. 보고서에 쓰지 말 것

- “안전기준 준수”, “ASHRAE 1,000 ppm 한도”, “OSHA 인증”, “NIOSH 인증”
- 유승하 표 EMERGENCY 2,000 ppm
- 구 V4 `0.35/0.35`, `CAUTION`, `R \ge 60`, 1,500 ppm = 위험
- `ondevice_ai/risk/fallback.py` 를 현재 Pi 정본으로 인용
- Satish를 산업 노출 한계처럼 인용. “2,500 ppm에서 인지 장애가 확정됐다”
- occupancy 출력을 위험 가중치로 설명
- \(B\)보다 낮은 CO₂를 위험으로 설명 (환기 개선)
- occupancy와 밀실 기준값 \(B\)를 같은 기능으로 설명
- “낙상 감지 완료”, “임상 무호흡 진단”
- FastAPI, SQLite3, WebSocket (정본 미구현)
- 엠대시(—), “A가 아니라 B” 구문

---

## 13. 참고문헌 (에이전트 각주용, 확인일 2026-08-30)

1. 환경부. 「실내공기질 관리법」 제5조; 「실내공기질 관리법 시행규칙」 제3조 [별표 2] (개정 2024.12.23.). 해설: 찾기쉬운 생활법령정보, 2026-07-15. https://www.easylaw.go.kr/CSP/CnpClsMain.laf?ccfNo=4&cciNo=1&cnpClsNo=2&csmSeq=1827
2. 법제처 국가법령정보센터. 실내공기질 관리법 시행규칙 [별표 2] 파일. https://www.law.go.kr/LSW/flDownload.do?bylClsCd=110201&flSeq=157776827&gubun=
3. 교육부. 「학교보건법 시행규칙」 제3조 [별표 4의2]. https://easylaw.go.kr/CSP/CnpClsMainBtr.laf?ccfNo=4&cciNo=3&cnpClsNo=2&csmSeq=1394&popMenu=ov
4. 고용노동부. 「산업안전보건기준에 관한 규칙」 제618조 제3호. 시행 2026.3.2. 고용노동부령 제450호. https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1016497817
5. OSHA. Carbon Dioxide, Chemical Data 183. PEL-TWA 5000 ppm; NIOSH IDLH 40,000 ppm. Updated 2024-05-23. https://www.osha.gov/chemicaldata/183
6. NIOSH. Pocket Guide to Chemical Hazards: Carbon dioxide. REL-TWA 5000 ppm, REL-STEL 30,000 ppm. https://www.cdc.gov/niosh/npg/npgd0103.html
7. ACGIH. Carbon Dioxide. TLV–TWA 5000 ppm, TLV–STEL 30,000 ppm. https://www.acgih.org/carbon-dioxide/
8. ASHRAE. Technical FAQ 35, Indoor CO2. https://www.ashrae.org/File%20Library/Technical%20Resources/Technical%20FAQs/TC-04.03-FAQ-35.pdf
9. ASHRAE. Interpretation IC 62-2001-06. https://www.ashrae.org/File%20Library/Technical%20Resources/Standards%20and%20Guidelines/Standards%20Intepretations/IC_62-2001-06.pdf
10. Trane. Engineers Newsletter vol. 31-3. https://www.trane.com/content/dam/Trane/Commercial/global/products-systems/education-training/engineers-newsletters/airside-design/adm_apn004_en.pdf
11. Persily A. Development and application of an indoor carbon dioxide metric. *Indoor Air*. 2022. https://doi.org/10.1111/ina.13059
12. Persily A. Indoor carbon dioxide metric analysis tool. NIST TN 2213. 2022. https://doi.org/10.6028/nist.tn.2213
13. Satish U, et al. Is CO2 an indoor pollutant? *Environ Health Perspect*. 2012;120:1671-1677. https://doi.org/10.1289/ehp.1104789
14. Cenci G, et al. Measurement of CO2 concentration for occupancy estimation in educational buildings. 2020. https://pmc.ncbi.nlm.nih.gov/articles/PMC7411428/
15. Cali D, et al. CO2 based occupancy detection algorithm. *Building and Environment*. 2015. https://doi.org/10.1016/j.buildenv.2014.12.008
16. Chourpiliadis C, Bhardwaj A. Physiology, Respiratory Rate. *StatPearls*. https://www.ncbi.nlm.nih.gov/books/NBK537306/
17. American Lung Association. Understanding Vital Signs: Respiratory Rate. https://www.lung.org/blog/respiratory-rate-vital-signs
