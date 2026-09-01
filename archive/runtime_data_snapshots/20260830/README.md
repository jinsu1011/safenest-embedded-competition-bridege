# 런타임 데이터 스냅샷 — 2026-08-30 19:07 (KST)

Pi(`/home/sandi/safenest-team-main`)에서 서비스를 멈추지 않고 뜬 스냅샷이다.
Pi의 `RaspberryPi/Runtime/data/`는 FIFO 회수 대상이라 파일이 계속 지워진다.
원격에서 기록을 보려면 이 폴더를 쓴다.

TTS 음성 모델(`ko_KR-kss-medium.onnx`, 63MB)은 GitHub 파일 크기 한도 때문에 제외했다.

## 내용물

| 경로 | 크기 | 설명 |
|---|---|---|
| `safenest.db` | 4.3MB | 2026-08-16 20:16 ~ 08-30 19:07 누적 기록. `sqlite3 .backup`으로 뜬 정합성 확인 완료 스냅샷 |
| `co2/20260830_09_co2.jsonl` | 11KB | ESP32 CO₂ 수신 로그, 37행 |
| `mmwave/20260830_10_mmwave.jsonl` | 65KB | ESP32 mmWave 수신 로그, 139행 |

thermal NPZ는 스냅샷 시점에 0개였다. 아래 "디스크 압박" 항목 참고.

## safenest.db

`sensor_snapshots` 6,723행, `risk_events` 5,912행.

날짜별 `sensor_snapshots`:

| 날짜 | 행 | 날짜 | 행 |
|---|---|---|---|
| 08-16 | 886 | 08-25 | 266 |
| 08-17 | 721 | 08-27 | 99 |
| 08-19 | 9 | 08-28 | 1,170 |
| 08-20 | 159 | 08-29 | 884 |
| 08-21 | 296 | 08-30 | 1,645 |
| 08-22 | 588 | | |

`risk_events` 상위 유형: `SENSOR_STATUS_CHANGED` 1,267, `RISK_LEVEL_CHANGED` 889,
`RUNTIME_ERROR` 715, `SENSOR_RECOVERED` 480, `SENSOR_OFFLINE` 444.

세 센서가 동시에 `LIVE`였던 스냅샷은 779행(11.6%)이고, 가장 흔한 조합은
`NO_DATA` 3종 2,646행이다. 대부분이 센서 미연결 상태에서 돌아간 기록이므로
통계를 낼 때 `mmwave_status`/`thermal_status`/`co2_status`로 먼저 거른다.

```bash
sqlite3 safenest.db "
  select datetime(timestamp,'unixepoch','localtime') t, risk_level, risk_score, event_type
  from risk_events
  where risk_level in ('WARNING','DANGER')
  order by timestamp desc limit 20;"
```

## ESP32 연결 로그 보는 법

`co2`/`mmwave` JSONL 각 행에 링크 상태 필드가 들어 있다.

- `device_id`: 송신 보드. 두 센서 모두 `esp32-01`.
- `boot_id`: 부팅마다 새로 생기는 값. **값이 바뀌면 보드가 재부팅한 것이다.**
- `sequence`: 보드가 매기는 송신 일련번호.
- `source_uptime_ms`: 보드 기준 가동 시간.
- `receive_monotonic`: Pi 기준 수신 시각.

```bash
# 부팅 횟수와 각 부팅의 수신 구간
python3 -c "
import json,sys,collections
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
b=collections.OrderedDict()
for r in rows: b.setdefault(r['boot_id'],[]).append(r)
for k,v in b.items():
    print(k[:8], len(v), 'rows', 'uptime', v[0]['source_uptime_ms'], '->', v[-1]['source_uptime_ms'])
" co2/20260830_09_co2.jsonl
```

이 스냅샷에서 확인되는 사실:

- CO₂ 로그의 25분 구간(09:11~09:36)에 `boot_id`가 **6개** 나타난다. 보드가 그
  사이에 여섯 번 재부팅했고, 매 부팅의 `source_uptime_ms`가 6초대에서 시작한다.
- mmWave 로그의 3분 구간은 `boot_id` 1개로 연속이다.
- `sequence` 값이 띄엄띄엄한 것은 유실이 아니다. CO₂ 기록은
  `SAFENEST_CO2_UPDATE_INTERVAL_SECONDS`(기본 60초) 간격으로 솎아서 저장한다.
  실제 유실을 보려면 같은 `boot_id` 안에서 `receive_monotonic` 간격을 본다.

## 디스크 압박 (스냅샷 시점 기준)

Pi 루트 파티션이 29GB 중 26GB 사용, 여유 1.6GB(95%)다.
`SensorDataLogger`의 `min_free_bytes` 기본값이 2GB라서 여유 공간이 그 아래인
동안에는 회수 루틴이 30초마다 돌면서 오래된 측정 파일부터 지운다.

실제로 19:00에 thermal 17MB·mmwave 5.3MB가 있었는데 19:03에 thermal은 0개,
mmwave는 진행 중인 1개만 남았다. 센서 용량 한도(mmwave 1GB, thermal 8.5GB)에는
한참 못 미치므로 원인은 한도가 아니라 여유 공간 부족이다.

**디스크를 비우기 전에는 새로 쌓이는 측정 데이터도 계속 지워진다.**
