당신은 Raspberry Pi에서 SafeNest Thermal의 안전 점검을 수행한다.

[P0가 무엇인가]
P0는 오탐 원인 분석을 시작하기 전의 “안전 경계 확인 단계”다.
목표는 HUMAN_FALL_PROXY라는 모델 결과 하나가 실제 emergency, GPIO/actuator,
문자·웹훅·푸시 등 외부 알림을 직접 일으키지 않는지 확인하는 것이다.

이번 작업은 P0 증거 수집만 한다.
TFP-0 이후 단계, 오탐 frame 분석, orientation 분석, 재학습은 절대 수행하지 않는다.

[절대 금지]
- 모델 교체·재학습·임계값 변경
- 센서 펌웨어 변경
- 서비스 restart/stop/start
- 실제 emergency, GPIO, actuator, SMS, webhook, push 알림 발생
- 실제 서비스에 가짜 HUMAN_FALL_PROXY 결과 주입
- raw thermal frame, raw UDP packet, 개인정보, 비밀번호·토큰 출력 또는 저장
- Git commit, push, 팀 저장소 수정

[알려진 팀 저장소]
https://github.com/jinsu1011/safenest-embedded-competition.git

이 저장소는 참고용이다. 실제 Pi에서 실행 중인 service와 설정이 가장 우선이다.

[확인해야 하는 것]
1. 실제 실행 중인 Thermal/SafeNest service와 PID
2. 해당 service의 실행 명령, 작업 디렉터리, 환경/설정 파일
3. 실제 runtime과 collector의 Git commit
4. 실제 활성 모델 selector, 모델 경로, SHA-256, 파일 크기, class order, preprocessing
5. public-SDT가 shadow/telemetry 전용인지, 아니면 risk fusion에 사용되는지
6. HUMAN_FALL_PROXY 하나가 emergency, actuator/GPIO, 외부 알림으로 직접 이어지는지
7. 조사 출력이 probability/telemetry로 제한되는지

[작업]

A. 실행 service와 process를 읽기 전용으로 찾는다.

date -Is
hostname
uname -a
ps auxww | grep -i -E 'thermal|safenest|ondevice|python' | grep -v grep
systemctl list-units --type=service --all | grep -i -E 'thermal|safenest|ondevice'
systemctl list-unit-files | grep -i -E 'thermal|safenest|ondevice'

발견한 각 <SERVICE_NAME>에 대해 실행한다.

systemctl cat <SERVICE_NAME>
systemctl show <SERVICE_NAME> -p ExecStart -p WorkingDirectory -p Environment -p EnvironmentFiles
journalctl -u <SERVICE_NAME> -n 300 --no-pager

발견한 각 <PID>에 대해 실행한다.

tr '\0' ' ' < /proc/<PID>/cmdline; echo
readlink -f /proc/<PID>/cwd

B. 실제 runtime root를 찾는다.

- systemctl의 WorkingDirectory, ExecStart, PID cwd에서 runtime root를 식별한다.
- runtime root 및 collector root로 보이는 곳에서 실행한다.

git rev-parse HEAD
git status --short
git remote -v

Git 저장소가 아니면 억측하지 말고 NOT_A_GIT_REPOSITORY로 기록한다.

C. 실제 모델과 알람 경로를 찾는다.

실제 runtime root와 service가 읽는 config 파일에서 아래 문자열을 검색한다.

grep -RniE 'active_runtime_selector|model_selector|HUMAN_FALL_PROXY|HUMAN_FALL|class_index|emergency_override|alarm_sink|actuator|gpio|webhook|sms|alert|shadow|telemetry|preprocessing' <RUNTIME_ROOT> <CONFIG_DIRECTORY> 2>/dev/null

실제 활성 모델 파일을 찾으면 실행한다.

sha256sum <ACTIVE_MODEL_PATH>
stat -c '%s %n' <ACTIVE_MODEL_PATH>

다음 원칙을 지킨다.

- HUMAN_FALL_PROXY가 risk score에 사용되는 것과 shadow/telemetry 전용은 다르다.
- proxy가 risk fusion에 참여하면 PUBLIC_SDT_NOT_SHADOW_ONLY로 기록한다.
- source 코드를 읽은 결과와 실제 Pi runtime에서 확인한 결과를 구분한다.
- actuator 또는 외부 알림이 없다고 추측하지 않는다. 설정과 실행 경로 증거가 없으면 UNVERIFIED다.

D. 테스트는 안전한 mock/unit test만 허용한다.

- 실제 service에는 어떠한 입력도 주입하지 않는다.
- hardware/network endpoint가 연결될 가능성이 있는 테스트는 실행하지 않는다.
- 기존 mock/unit test가 있고 hardware·network 호출이 없음을 코드로 확인한 경우에만 실행한다.
- 안전한 테스트가 없으면 BLOCKED_UNSAFE_TEST_PATH로 기록한다.
- 실제 알림을 발생시키는 테스트는 절대 실행하지 않는다.

E. 팀 저장소가 Pi에 없을 경우에만, 참고용 읽기 전용 clone을 만든다.

git clone --depth 1 https://github.com/jinsu1011/safenest-embedded-competition.git /tmp/safenest-team-p0-review
git -C /tmp/safenest-team-p0-review rev-parse HEAD

이 clone은 실제 Pi runtime을 대체하지 않는다. 수정·commit·push하지 않는다.

F. 민감정보를 제거한 결과를 /tmp/p0_runtime_evidence.json에 작성한다.

반드시 아래 필드를 포함한다.

{
  "roadmap_step": "P0",
  "status": "PASS_OR_BLOCKED",
  "active_service": "",
  "active_process_command": "",
  "runtime_root": "",
  "runtime_repository_commit": "",
  "collector_repository_commit": "",
  "active_model_selector": "",
  "model_path": "",
  "model_sha256": "",
  "model_size_bytes": null,
  "model_class_order": [],
  "preprocessing_id": "",
  "alarm_mode": "",
  "public_sdt_shadow_or_telemetry_only": "PASS_OR_FAIL_OR_UNVERIFIED",
  "proxy_source_review": {
    "emergency_path": "PASS_OR_FAIL_OR_UNVERIFIED",
    "actuator_path": "PASS_OR_FAIL_OR_UNVERIFIED",
    "external_alert_path": "PASS_OR_FAIL_OR_UNVERIFIED",
    "evidence_paths": []
  },
  "proxy_isolated_mock_test": {
    "executed": false,
    "result": "PASS_OR_FAIL_OR_BLOCKED_UNSAFE_TEST_PATH",
    "command": ""
  },
  "diagnostic_output_probability_or_telemetry_only": "PASS_OR_FAIL_OR_UNVERIFIED",
  "blockers": [],
  "sensitive_data_removed": true
}

[최종 응답]
한국어로 아래만 보고한다.

- P0 판정: PASS 또는 BLOCKED
- 실제 실행 service와 runtime root
- runtime/collector commit
- 활성 모델 selector, SHA-256, preprocessing
- public-SDT가 shadow/telemetry 전용인지 여부
- proxy의 emergency/actuator/external alert 검사 결과
- 실행한 안전한 mock test 또는 실행하지 못한 이유
- /tmp/p0_runtime_evidence.json 경로
- “TFP-0은 수행하지 않았다.”