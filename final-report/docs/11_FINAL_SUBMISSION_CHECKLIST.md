# 11_FINAL_SUBMISSION_CHECKLIST

상태: **PASS** / **MISSING** / **NOT VERIFIED**
예선 마감: 9월 3일(목) — 자유공모 세부안내 p.3

## REPORT (개발완료보고서)

| | 항목 | 상태 | 비고 |
|---|---|---|---|
| ☑ | 공식 7개 필수 항목 모두 포함 | **PASS** | 1·2·3·4·5·6·7 전부 배치 |
| ☑ | 콘텐츠 20페이지 이내 (표지 제외) | **PASS** | 표지 1 + 콘텐츠 20 = 21슬라이드 |
| ☑ | 공식 분량 배분 3 / 10 / 5 / 2 | **PASS** | P1–3 / P4–13 / P14–18 / P19–20 |
| ☑ | PPT 방식 작성 | **PASS** | PptxGenJS 생성, 모든 텍스트·표·도형 편집 가능 |
| ☑ | PPTX → PDF 변환 | **PASS** | Keynote 14 export, 21페이지, 13.32×7.5 in |
| ☑ | PDF가 PPTX와 동일 레이아웃 | **PASS** | PDF를 별도 설계하지 않고 PPTX에서 직접 export |
| ☑ | 소스코드 링크 삽입 | **PASS** | P3, 실제 URL·하이퍼링크 |
| ☐ | 시연동영상 링크 삽입 | **MISSING** | P3에 `[최종 시연동영상 URL 입력 필요]` 플레이스홀더 |
| ☐ | 공식 파일명 | **MISSING** | 현재 `..._개발완료보고서_DRAFT.pdf`. 최종본은 `_DRAFT` 제거 필요 |
| ☐ | 팀번호 확인 | **NOT VERIFIED** | 표지 `[팀번호 확인 필요]_가만있어도SANDI` |
| ☑ | 한글 렌더링 확인 | **PASS** | 21페이지 전부 육안 확인, 폰트 대체·깨짐 없음 |
| ⚠ | PDF 텍스트 추출 | **NOT VERIFIED** | Keynote 서브셋 폰트로 복사·검색 시 한글 깨짐. 시각적 표시는 정상 |
| ☑ | 저작권 안전 서체 | **PASS** | macOS 기본 Apple SD Gothic Neo, 폰트 파일 미배포 |
| ☑ | 저작권 안전 이미지 | **PASS** | 전부 팀 자체 촬영·CAD·측정데이터. 스톡·생성 이미지 0건 |
| ☑ | 이미지 PPTX 내장 | **PASS** | 7개 전부 내장, 외부·절대경로 링크 0건 |
| ☑ | 팀명 규칙 | **PASS** | 가만있어도SANDI = 15 Byte, 영문 대문자, 특수문자·'팀' 없음 |

## GITHUB (소스코드)

| | 항목 | 상태 | 비고 |
|---|---|---|---|
| ☑ | 저장소 존재·URL 확정 | **PASS** | `github.com/jinsu1011/safenest-embedded-competition` |
| ☐ | 공식 명명 규칙 준수 | **MISSING** | 규격 `2026ESWContest_free_팀명` 미준수. **사용자 승인 없이 rename하지 않음** |
| ☐ | Public 공개 상태 | **NOT VERIFIED** | 수상 시 Public 유지 의무(세부안내 5-마). 현재 상태 미확인 |
| ☑ | 자격증명 노출 없음 | **PASS** | 패키지 보안 감사에서 39개 파일 제외, 개인키·실제 `.env` 0건 |
| ☐ | OSS 라이선스 준수 | **NOT VERIFIED** | **SDT Dataset(TU Wien/Zenodo 4124309)의 CC-BY-4.0 메타 vs 비상업 연구 제한 충돌 확인 필요** |
| ☐ | 저장소 LICENSE 파일 | **NOT VERIFIED** | 최상위 LICENSE 존재 여부 미확인 |
| ☑ | 외부 자산 출처 보고서 기재 (규정 제10조③) | **PASS** | P6에 데이터셋 3종·라이브러리 명시 |
| ☐ | 강유나 브랜치 병합 | **MISSING** | `yuname121/integration` @ `9e4ddfe…` 미병합 — 보고서 기재와 저장소 불일치 위험 |

## VIDEO (시연동영상)

| | 항목 | 상태 |
|---|---|---|
| ☐ | 3분 이내 | **MISSING** |
| ☐ | 720p 이상 | **MISSING** |
| ☐ | 실제 작품 시연 포함 | **MISSING** |
| ☐ | 작품 설명 포함 | **MISSING** |
| ☐ | YouTube 업로드 | **MISSING** |
| ☐ | 제목 `2026ESWContest_자유공모_가만있어도SANDI_시연동영상` | **MISSING** |
| ☐ | 보고서에 URL 삽입 | **MISSING** |
| ☑ | 콘티 확보 | **PASS** — `03_Evidence/Demo_Materials/SafeNest_3분_시연영상_콘티.pdf` |

## 기타 예선 제출물

| | 항목 | 상태 |
|---|---|---|
| ☐ | 참가신청서 (엑셀, `2026ESWContest_자유공모_가만있어도SANDI_참가신청서`) | **NOT VERIFIED** — 패키지에 없음 |
| ☐ | 개발완료보고서 PDF (최종본) | **MISSING** — 현재 DRAFT |
| ☑ | GitHub URL 준비 | **PASS** (명명 규칙은 별도) |
| ☐ | YouTube URL 준비 | **MISSING** |
| ☐ | 구글폼 제출 | **NOT VERIFIED** |
| ☑ | 팀 구성 1~5인 | **PASS** — 5인 |
| ☐ | 전원 참가신청서 기재·개인정보 동의 | **NOT VERIFIED** |

## 기술 증거 보완 (제출 전 권장)

| | 항목 | 상태 |
|---|---|---|
| ☐ | 4센서 동시 수신 실기기 로그 | **MISSING (최우선)** |
| ☐ | 통합 HIL (실입력 → Risk → 경보) | **MISSING** |
| ☐ | 실센서 구동 Web·LCD 화면 캡처 | **MISSING** |
| ☐ | 최종 통합 하드웨어 사진 | **MISSING** |
| ☐ | 완성 하우징 실물 | **MISSING** |
| ☐ | Wi-Fi 절단/복구 시험 | **MISSING** |
| ☐ | CO₂ 센서 분리 60초 원시 로그 | **MISSING** |
| ☐ | 공식 통계 원문 확인 (고용노동부·산안법 조문) | **NOT VERIFIED** |
| ☐ | CO₂ 임계값 기관 근거 | **NOT VERIFIED** |
| ☑ | mmWave·CO₂·Thermal 채널별 실기기 증거 | **PASS** |
| ☑ | fail-closed 소프트웨어 검증 | **PASS** — 본 세션 57건 실행 통과 |

---

## 종합 판정

**DRAFT READY** — 최종 제출본으로 승격 불가.

승격 차단 사유 (3건 모두 해소 필요):
1. 시연동영상 부재 (예선 필수 제출물)
2. GitHub 저장소 명명 규칙 미준수
3. 팀번호 미확인 (표지·파일명)

추가로, 강유나 브랜치 미병합은 **보고서 기재와 제출 저장소가 불일치**할 수 있어 제출 전 반드시 정리해야 한다.
