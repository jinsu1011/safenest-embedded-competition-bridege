/*
 * SafeNest ESP32 sensor node v3 (field bring-up build)
 * =====================================================
 *
 * 이 스케치는 esp32_sensor_node_mhz19b_v2 를 기반으로, "하드웨어는 다 됐는데
 * 값이 제대로 안 들어온다"는 현장 증상을 잡기 위해 다시 쓴 버전입니다.
 * 전송 프로토콜(SafeNest TCP v1 / Thermal UDP v1)은 한 바이트도 바뀌지 않았고,
 * 라즈베리파이 Runtime 은 수정 없이 그대로 이 노드를 받습니다.
 *
 * v2 대비 실제로 고친 것 (자세한 근거는 docs/FIELD_DEBUG_KO.md):
 *
 *  1) Thermal 프레임이 조용히 전부 버려지던 문제
 *     v2 는 MI48 헤더 워드 배치를 capture[5]=max, capture[6]=min, capture[7]=crc
 *     로 "가정"하고, 어긋나면 프레임을 drop 했습니다. 이 배치는 이 저장소 어디에도
 *     검증 근거가 없고(검증된 research/thermal_ai 레퍼런스 펌웨어는 헤더를 아예
 *     읽지 않습니다), 어긋나면 열화상이 100% 사라집니다.
 *     v3 은 부팅 후 첫 프레임들에서 헤더 워드를 스캔해 min/max 인덱스를 스스로
 *     찾아내고(THERMAL_HEADER_PROBE_FRAMES), 찾지 못하면 검증을 끄고 계속
 *     전송합니다. 검증 실패는 카운터와 로그로만 남습니다. 전송을 막는 판정으로
 *     쓰려면 THERMAL_STRICT_VALIDATION 를 켜세요(기본 꺼짐).
 *
 *  2) READY 핀이 죽어 있거나 붕 떠 있을 때 구분이 안 되던 문제
 *     v3 은 부팅 시 READY 핀을 실제로 관찰해서 (stuck-high / stuck-low / pulsing)
 *     세 가지를 판별하고, stuck 이면 자동으로 I2C 폴링 모드로 내려갑니다.
 *     [thermal] 로그에 지금 어떤 모드로 도는지 항상 찍습니다.
 *
 *  3) MH-Z19B UART 프레임 정렬(sync) 문제
 *     v2 는 available()>=9 이면 9바이트를 그대로 읽어 frame[0]!=0xFF 이면
 *     checksum 실패로 셌습니다. 한 번 바이트가 밀리면(부팅 노이즈, 반이중 배선)
 *     영원히 실패만 셉니다. v3 은 링버퍼에서 0xFF 0x86 을 찾아 재동기화하고,
 *     헤더불일치 / 체크섬불일치 / 타임아웃 / 짧은프레임을 각각 따로 셉니다.
 *
 *  4) "왜 null 인지"를 알 수 없던 문제
 *     v3 은 1초에 한 번 [tx] 줄로 실제로 나간 JSON 을 그대로 찍고, [why] 줄로
 *     각 필드가 null 인 이유(NEVER_SEEN / STALE / PREHEAT / OUT_OF_RANGE)를
 *     찍습니다. 시리얼만 보면 어느 센서가 왜 죽었는지 바로 나옵니다.
 *
 *  5) 부팅 자가진단
 *     setup() 마지막에 I2C 스캔, MR60 UART 바이트 유입, MH-Z19B 첫 응답,
 *     PIR 핀 레벨, Thermal ID 를 모두 확인해 [selftest] 로 요약합니다.
 *
 * 배선 (v2 와 동일, ESP32 Dev Module / WROOM-32):
 *   MR60BHA2   UART2  RX=GPIO16 (MR60 TX)  TX=GPIO17 (MR60 RX)  115200
 *   MH-Z19B    UART1  RX=GPIO32 (MHZ TX)   TX=GPIO33 (MHZ RX)   9600 8N1
 *              전원은 반드시 5V(4.5~5.5V, 피크 150mA). 3.3V 레일 금지.
 *   PIR        GPIO13 (digital in)
 *   Thermal    I2C SDA=21 SCL=22 / SPI SCLK=18 MISO=19 MOSI=23
 *              CS=27 READY=26 RESET=25
 *
 * 필요한 라이브러리: Seeed_Arduino_mmWave
 * secrets.h 는 이 스케치 폴더에 직접 만듭니다 (secrets.h.example 참고).
 */

#include <Arduino.h>
#include <esp_system.h>
#include <freertos/event_groups.h>
#include <freertos/semphr.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <SPI.h>
#include <errno.h>
#include <lwip/sockets.h>
#include <ESPmDNS.h>
#include <WiFiMulti.h>
#include "Seeed_Arduino_mmWave.h"
#include "secrets.h"

// =============================================================================
// 신원 / 버전
// =============================================================================
constexpr char DEVICE_ID[] = "esp32-01";
constexpr char NODE_FIRMWARE_VERSION[] =
    "safenest-esp32-sensor-node/2.0.0-field.1";
constexpr char DIAGNOSTIC_BUILD_ID[] = "v3-field-bringup-20260901";
constexpr char MMWAVE_SCHEMA_VERSION[] = "1.3";
constexpr char CO2_SENSOR_MODEL[] = "MH-Z19B";
constexpr char CO2_EVENT_IDENTITY_CLASS[] = "INFERRED_UART_SAMPLE";
char bootId[33] = {};

// =============================================================================
// 핀 배치
// =============================================================================
constexpr int PIN_I2C_SDA = 21;
constexpr int PIN_I2C_SCL = 22;
constexpr int PIN_PIR = 13;
constexpr int PIN_MMWAVE_RX = 16;
constexpr int PIN_MMWAVE_TX = 17;
constexpr int PIN_MHZ19_RX = 32;
constexpr int PIN_MHZ19_TX = 33;
constexpr int PIN_THERMAL_SCLK = 18;
constexpr int PIN_THERMAL_MISO = 19;
constexpr int PIN_THERMAL_MOSI = 23;
constexpr int PIN_THERMAL_CS = 27;
constexpr int PIN_THERMAL_READY = 26;
constexpr int PIN_THERMAL_RESET = 25;

constexpr uint32_t USB_BAUD = 115200;
constexpr uint32_t MMWAVE_BAUD = 115200;
constexpr uint32_t MHZ19_BAUD = 9600;
constexpr uint32_t THERMAL_SPI_HZ = 8000000;
constexpr uint16_t THERMAL_UDP_PORT = 5005;

// =============================================================================
// 스케줄 / 임계값
// =============================================================================
// 10 Hz. mmwave.breath_phase 의 PHASE_MAX_AGE_MS 가 500 ms 이므로 1 Hz 로 보내면
// Pi 의 300-sample 창이 절대 안 찹니다. LCD/대시보드는 남는 패킷을 무시합니다.
constexpr uint32_t TELEMETRY_PERIOD_MS = 100;
constexpr uint32_t PIR_PERIOD_MS = 20;
constexpr uint32_t CO2_UART_SAMPLE_PERIOD_MS = 5000;
constexpr uint32_t CO2_UART_RESPONSE_TIMEOUT_MS = 300;
// CO2 예열을 두 갈래로 나눕니다.
//
// 지금까지는 부팅 후 3분 동안 co2_ppm 을 통째로 null 로 막았습니다. 그런데
// 이 타이머는 "센서 전원 인가" 가 아니라 "ESP 부팅" 기준이라, 센서가 몇 시간
// 켜져 있었어도 ESP 를 다시 굽는 순간 또 3분을 기다려야 했습니다. 화면에
// 값이 안 뜨는 시간의 대부분이 이것 때문이었습니다.
//
//   CO2_VALUE_WARMUP_MS  : 화면/telemetry 에 값을 실어 보내기까지. 0 = 즉시.
//                          체크섬이 맞는 실측값이므로 표시용으로는 문제 없습니다.
//   CO2_MODEL_PREHEAT_MS : co2_preheat_complete(=AI 입력 자격)를 주기까지.
//                          Winsen 규격 3분을 그대로 지킵니다. 예열 전 값을
//                          C-B6 / H150 모델에 넣으면 slope 가 오염됩니다.
//
// 즉 값은 바로 보이고, AI 만 규격대로 기다립니다. 시연 때 기다리기 곤란하면
// 시리얼에서 'p' 를 눌러 모델 예열을 즉시 완료 처리할 수 있습니다.
constexpr uint32_t CO2_VALUE_WARMUP_MS = 0;
constexpr uint32_t CO2_MODEL_PREHEAT_MS = 180000;  // Winsen 규격 3분
constexpr uint16_t CO2_PPM_MIN_ACCEPTED = 350;
constexpr uint16_t CO2_PPM_MAX_ACCEPTED = 10000;
constexpr uint32_t MMWAVE_STALE_MS = 10000;
constexpr uint32_t CO2_STALE_MS = 15000;
constexpr uint32_t PHASE_MAX_AGE_MS = 500;
constexpr uint32_t PRESENCE_MAX_AGE_MS = 5000;

constexpr uint32_t HEALTH_LOG_PERIOD_MS = 10000;
constexpr uint32_t DIAG_LOG_PERIOD_MS = 10000;
constexpr uint32_t TX_LOG_PERIOD_MS = 1000;  // [tx] / [why] 주기

// 진단 로그 UDP 미러.
//
// ESP32 를 맥북 USB 가 아니라 충전기/외부 전원으로 돌리면 시리얼이 끊깁니다.
// 그래서 [health]/[ai]/[tx]/[why]/[link] 를 서브넷 브로드캐스트로도 뿌립니다.
// 같은 Wi-Fi 의 어떤 PC 에서든 이 포트를 열어두면 시리얼과 똑같은 줄이 보입니다.
//
// UDP 라서 유실되면 그 줄만 사라지고 노드는 영향을 받지 않습니다. TCP 텔레메트리
// 가 뮤텍스를 쥐고 있는 동안에는 건너뛰므로 본 경로를 방해하지 않습니다.
constexpr uint16_t DIAG_LOG_UDP_PORT = 5006;

// =============================================================================
// 링크 타이밍 (v2 에서 현장 측정으로 정해진 값 그대로 유지)
// =============================================================================
constexpr uint32_t PI_PACKET_DEADLINE_MS = 2000;
constexpr uint32_t TELEMETRY_GAP_WARN_MS = 1500;
constexpr uint32_t TCP_WRITE_WARN_MS = 150;
constexpr uint32_t TCP_WRITE_DEADLINE_MS = 800;
constexpr uint32_t TCP_CONNECT_TIMEOUT_MS = 1500;
constexpr uint32_t TCP_MUTEX_WARN_MS = 100;
constexpr uint32_t TCP_MUTEX_MAX_WAIT_MS = 250;
// 좀비 소켓 탈출 임계값.
//
// fail-fast write 가 0바이트로 타임아웃하면 그 패킷은 Pi 에 닿지 않았으므로
// 세션을 유지하는 게 맞습니다(일시적 혼잡). 그런데 무선 손실로 Pi 의 FIN/RST 이
// 도착하지 못하면 ESP 는 상대가 이미 닫은 소켓을 붙들고, lwIP 송신 버퍼가 미확인
// 데이터로 가득 차 send() 가 영원히 EAGAIN 을 냅니다. 현장 로그에서 정확히 이
// 상태였습니다: tcp=up, peer_closed=0, 그런데 sent 가 37 에서 멈추고
// zero_writes=401 / errno=11 이 400회 넘게 반복.
//
// 연속 실패가 이 횟수를 넘으면 소켓이 죽은 것으로 보고 강제로 끊어 재접속합니다.
// 5회 × 800 ms = 약 4 초로, Pi 의 5 초 수신 데드라인 안쪽입니다.
constexpr uint32_t TCP_MAX_CONSECUTIVE_WRITE_TIMEOUTS = 5;
// Wi-Fi 레벨 복구 임계값.
//
// WiFi.status() 가 WL_CONNECTED 이고 RSSI 도 -47 로 멀쩡한데 실제로는 프레임이
// 양방향 모두 안 지나가는 상태가 현장에서 관측되었습니다(핫스팟이 클라이언트를
// 조용히 내보냈는데 STA 는 모르는 경우). 이때 TCP 만 재접속해봐야 영원히
// connect timeout 입니다. 소켓이 아니라 결합 자체를 다시 해야 합니다.
//
// 1초 간격 재시도이므로 8회면 약 8초. Pi 의 수신 데드라인과 무관한 로컬 판단입니다.
constexpr uint32_t WIFI_REASSOCIATE_AFTER_CONNECT_FAILURES = 8;
constexpr uint32_t UDP_DATAGRAM_WARN_MS = 40;
constexpr uint32_t UDP_CHUNK_GAP_MS = 20;
constexpr uint32_t UDP_YIELD_TO_TCP_MAX_MS = 80;
constexpr uint32_t HEAP_RECLAIM_LOW_WATER_BYTES = 48000;
constexpr uint32_t UDP_ENOMEM_BACKOFF_MIN_MS = 250;
constexpr uint32_t UDP_ENOMEM_BACKOFF_MAX_MS = 2000;
constexpr uint32_t UDP_SLOW_TCP_HOLDOFF_MS = 250;
constexpr uint32_t UDP_MAX_CONSECUTIVE_FAILURES = 10;

// =============================================================================
// Thermal (MI48xx + MI0801/MI0802, 80 x 62)
// =============================================================================
constexpr uint8_t THERMAL_ADDRESS_A = 0x40;
constexpr uint8_t THERMAL_ADDRESS_B = 0x41;

constexpr uint8_t REG_EVK_TEST = 0x00;
constexpr uint8_t REG_SENSOR_POWERUP = 0xB0;
constexpr uint8_t REG_FRAME_MODE = 0xB1;
constexpr uint8_t REG_FW_VERSION_1 = 0xB2;
constexpr uint8_t REG_FW_VERSION_2 = 0xB3;
constexpr uint8_t REG_FRAME_RATE = 0xB4;
constexpr uint8_t REG_STATUS = 0xB6;
constexpr uint8_t REG_SENSOR_TYPE = 0xBA;

constexpr uint8_t STATUS_DATA_READY = 0x10;
constexpr uint8_t STATUS_BOOTING = 0x20;
constexpr uint8_t MODE_CONTINUOUS = 0x02;

constexpr size_t THERMAL_WIDTH = 80;
constexpr size_t THERMAL_HEIGHT = 62;
constexpr size_t THERMAL_PIXEL_COUNT = THERMAL_WIDTH * THERMAL_HEIGHT;  // 4960
constexpr size_t THERMAL_HEADER_WORDS = 80;
constexpr size_t THERMAL_CAPTURE_WORDS =
    THERMAL_HEADER_WORDS + THERMAL_PIXEL_COUNT;

// MI48 FRAME_RATE 은 ~25 FPS 원본의 분주값입니다. 25 -> 약 1.0 FPS.
// 1 fps 는 9개 datagram/초 이므로 1 Hz TCP 와 경합하지 않습니다.
constexpr uint8_t THERMAL_FRAME_RATE_DIVIDER = 25;

// 헤더 배치 자동 탐색: 처음 이 개수의 정상 프레임 동안 헤더 워드에서
// 픽셀 min/max 와 일치하는 인덱스를 찾습니다. 못 찾으면 검증을 끕니다.
constexpr uint8_t THERMAL_HEADER_PROBE_FRAMES = 8;
// true 로 바꾸면 헤더 검증 실패 프레임을 실제로 버립니다. 기본은 "세기만" 합니다.
// 현장에서 열화상이 안 나오는 원인 1순위가 바로 이 검증이었기 때문입니다.
constexpr bool THERMAL_STRICT_VALIDATION = false;
// READY 핀 판별 관찰 창. THERMAL_FRAME_RATE_DIVIDER=25(~1 fps)에서 최소
// 두 프레임 주기를 덮어야 rise 를 볼 기회가 생깁니다.
constexpr uint32_t THERMAL_READY_PROBE_MS = 3000;

// =============================================================================
// SafeNest 프로토콜 상수 (Pi Runtime 계약. 변경 금지)
// =============================================================================
constexpr uint8_t PROTOCOL_VERSION = 1;
constexpr uint8_t PACKET_TELEMETRY_JSON = 1;
constexpr uint8_t PACKET_THERMAL_U16_BE = 2;
constexpr size_t PACKET_HEADER_SIZE = 16;
constexpr size_t THERMAL_META_SIZE = 16;

constexpr char THERMAL_UDP_MAGIC[] = "SNTU";
constexpr uint8_t THERMAL_UDP_VERSION = 1;
constexpr size_t THERMAL_UDP_HEADER_SIZE = 32;
constexpr size_t THERMAL_UDP_DATAGRAM_SIZE = 1200;
constexpr size_t THERMAL_UDP_CHUNK_SIZE =
    THERMAL_UDP_DATAGRAM_SIZE - THERMAL_UDP_HEADER_SIZE;  // 1168
constexpr size_t THERMAL_PAYLOAD_SIZE =
    THERMAL_META_SIZE + THERMAL_PIXEL_COUNT * sizeof(uint16_t);  // 9936
constexpr uint16_t THERMAL_UDP_CHUNK_COUNT =
    (THERMAL_PAYLOAD_SIZE + THERMAL_UDP_CHUNK_SIZE - 1) / THERMAL_UDP_CHUNK_SIZE;

// MH-Z19B read-concentration command 0x86
constexpr uint8_t MHZ19_READ_CMD[9] = {0xFF, 0x01, 0x86, 0x00, 0x00,
                                       0x00, 0x00, 0x00, 0x79};

// =============================================================================
// 타입
// =============================================================================
enum class Mhz19Txn : uint8_t { IDLE, AWAIT_RESPONSE };

enum class ThermalReadyMode : uint8_t {
  UNKNOWN,
  READY_PIN,       // READY 핀이 정상적으로 토글함
  I2C_POLL,        // READY 핀을 못 믿어서 I2C STATUS 폴링으로 내려감
  CAMERA_ABSENT,   // 카메라 자체가 없음 (DISABLED 는 esp32-hal-gpio.h 매크로라 못 씀)
};

// 왜 null 인지 사람이 읽을 수 있게 남기는 사유 코드.
enum class NullReason : uint8_t {
  OK,
  NEVER_SEEN,
  STALE,
  PREHEAT,
  OUT_OF_RANGE,
  NOT_FINITE,
};

struct TelemetrySnapshot {
  uint32_t sequence;
  uint32_t uptimeMs;
  float respirationRate;
  float heartRate;
  uint16_t co2Ppm;
  bool pirMotion;
  bool respirationValid;
  bool heartValid;
  bool co2Valid;
  bool phaseSamplePresent;
  uint32_t co2MeasurementEventId;
  uint32_t co2MeasurementMonotonicMs;
  bool co2MeasurementEventValid;
  bool co2Preheat;
  bool humanDetectedRaw;
  bool humanDetectedKnown;
  float totalPhase;
  float breathPhase;
  float heartPhase;
  uint32_t phaseTimestampMs;
  uint32_t phaseSequence;
  // 진단용. JSON 에는 안 나갑니다.
  NullReason respReason;
  NullReason heartReason;
  NullReason co2Reason;
};

struct ThermalTxFrame {
  uint32_t frameSequence;
  uint32_t uptimeMs;
  uint16_t minimumRaw;
  uint16_t maximumRaw;
  uint16_t pixels[THERMAL_PIXEL_COUNT];
};

struct TcpWriteReport {
  size_t bytesWritten;
  uint32_t elapsedMs;
  uint32_t longestStallMs;
  uint16_t zeroWrites;
  uint16_t partialWrites;
  int lastErrno;
  bool connectedAtEnd;
};

enum class ThermalSendResult {
  Sent,
  Preempted,
  Failed,
  Suppressed,
  Deferred,
};

// =============================================================================
// 전역 객체
// =============================================================================
HardwareSerial mmWaveSerial(2);
HardwareSerial mhz19Serial(1);

// Seeed 라이브러리의 isHumanDetected() 는 "아직 리포트를 못 받았다"와
// "사람이 없다"를 구분하지 못합니다. handleType() 을 가로채서 리포트 도착
// 자체를 기록해야 tri-state(true/false/unknown) 가 성립합니다.
class SafeNestMR60BHA2 : public SEEED_MR60BHA2 {
 public:
  bool handleType(uint16_t type, const uint8_t *data,
                  size_t dataLength) override {
    ++framesParsed_;
    if (type == static_cast<uint16_t>(TypeHeartBreath::ReportHumanDetection)) {
      if (dataLength < 1) return false;  // 벤더 핸들러의 무방비 data[0] 접근 차단
      presenceRaw_ = data[0] != 0;
      presencePending_ = true;
    }
    lastType_ = type;
    return SEEED_MR60BHA2::handleType(type, data, dataLength);
  }

  bool takePresence(bool &value) {
    if (!presencePending_) return false;
    presencePending_ = false;
    value = presenceRaw_;
    return true;
  }

  uint32_t framesParsed() const { return framesParsed_; }
  uint16_t lastType() const { return lastType_; }

 private:
  bool presenceRaw_ = false;
  bool presencePending_ = false;
  uint32_t framesParsed_ = 0;
  uint16_t lastType_ = 0;
};

// 여러 AP 를 등록해두고 잡히는 쪽에 붙습니다. 랩 공유기 / 핫스팟을 오갈 때
// 펌웨어를 다시 굽지 않아도 됩니다.
WiFiMulti wifiMulti;

SafeNestMR60BHA2 mmWave;
SPIClass thermalSpi(VSPI);

QueueHandle_t telemetryQueue = nullptr;
QueueHandle_t thermalQueue = nullptr;
EventGroupHandle_t networkEvents = nullptr;
SemaphoreHandle_t networkTxMutex = nullptr;
constexpr EventBits_t TCP_CRITICAL_BIT = BIT0;

// ~10 KiB 짜리들은 태스크 스택에 두면 넘칩니다. 전역이 의도된 배치입니다.
uint16_t thermalCapture[THERMAL_CAPTURE_WORDS];
ThermalTxFrame thermalProducerFrame;
ThermalTxFrame thermalNetworkFrame;
uint8_t thermalUdpDatagram[THERMAL_UDP_DATAGRAM_SIZE];

// =============================================================================
// 센서 상태 (core 1 = loop() 소유)
// =============================================================================
float respirationRate = NAN;
float heartRate = NAN;
float totalPhase = NAN;
float breathPhase = NAN;
float heartPhase = NAN;
uint16_t co2Ppm = 0;
bool pirMotion = false;
bool humanDetectedRaw = false;
bool phaseSamplePresent = false;

uint32_t lastRespirationMs = 0;
uint32_t lastHeartMs = 0;
uint32_t lastPresenceMs = 0;
uint32_t lastCo2Ms = 0;
uint32_t lastPhaseMs = 0;
uint32_t lastPirPollMs = 0;
uint32_t lastCo2PollMs = 0;
uint32_t lastTelemetryMs = 0;
uint32_t lastHealthLogMs = 0;
uint32_t lastLinkLogMs = 0;
uint32_t lastTxLogMs = 0;
uint32_t lastThermalStatusPollMs = 0;

uint32_t telemetrySequence = 0;
uint32_t phaseSequence = 0;
uint32_t loopIterations = 0;

// mmWave 진단
uint32_t mmWaveUpdateSuccesses = 0;
uint32_t mmWaveUpdateMisses = 0;
uint32_t lastMmWaveUpdateMs = 0;
uint32_t mmWaveBreathSamples = 0;
uint32_t mmWaveHeartSamples = 0;
uint32_t mmWavePresenceReports = 0;

// CO2 진단
uint32_t co2MeasurementEventId = 0;
uint32_t co2MeasurementMonotonicMs = 0;
bool co2MeasurementEventValid = false;
Mhz19Txn mhz19Txn = Mhz19Txn::IDLE;
uint32_t mhz19RequestSentMs = 0;
uint32_t co2ChecksumFailures = 0;
uint32_t co2HeaderFailures = 0;
uint32_t co2TimeoutFailures = 0;
uint32_t co2ShortFrameFailures = 0;
uint32_t co2ResyncEvents = 0;
uint32_t co2RangeRejects = 0;
uint32_t co2AcceptedSamples = 0;
uint32_t co2RequestsSent = 0;
uint16_t co2LastUartPpm = 0;
uint8_t mhz19RxBuffer[32];
uint8_t mhz19RxLength = 0;

// Thermal 진단
uint8_t thermalAddress = 0;
bool thermalStarted = false;
ThermalReadyMode thermalReadyMode = ThermalReadyMode::UNKNOWN;
uint32_t thermalSequence = 0;
uint32_t thermalCaptureAttempts = 0;
uint32_t thermalReadyByPin = 0;
uint32_t thermalReadyByI2c = 0;
uint32_t thermalCaptureMaxMs = 0;
uint32_t thermalStatusQueryFailures = 0;
uint32_t thermalHeaderMismatches = 0;
uint32_t thermalFlatFrames = 0;  // 모든 픽셀이 동일 = SPI 배선/CS 문제 신호
uint32_t thermalStrictDrops = 0;
uint32_t thermalReadyStuckAfterRead = 0;
uint32_t thermalReadyDemotions = 0;
uint8_t thermalHeaderProbes = 0;
int8_t thermalHeaderMinIndex = -1;
int8_t thermalHeaderMaxIndex = -1;
bool thermalHeaderLayoutResolved = false;
bool thermalHeaderLayoutGiveUp = false;
uint16_t thermalLastHeader[16] = {};

// =============================================================================
// 네트워크 카운터 (core 0 의 네트워크 태스크가 유일한 writer)
// =============================================================================
volatile uint32_t telemetryQueueOverwrites = 0;
volatile uint32_t thermalQueueOverwrites = 0;
volatile uint32_t tcpConnectionFailures = 0;
volatile uint32_t tcpSendFailures = 0;
volatile uint32_t thermalUdpFramesSent = 0;
volatile uint32_t thermalFramesPreempted = 0;
volatile uint32_t thermalTcpYields = 0;
volatile uint32_t thermalUdpSendFailures = 0;
volatile uint32_t heapReclaims = 0;
volatile uint32_t heapReclaimSkippedTcp = 0;
volatile uint32_t udpHoldoffEvents = 0;
volatile uint32_t udpHoldoffUntilMs = 0;
volatile uint32_t udpBackoffMs = 0;
volatile uint32_t tcpWriteTimeouts = 0;
volatile uint32_t tcpZombieRecoveries = 0;
volatile uint32_t wifiReassociations = 0;
volatile uint32_t tcpSessions = 0;
volatile uint32_t tcpDrops = 0;
volatile uint32_t tcpShortSessions = 0;
volatile uint32_t tcpPeerClosed = 0;
volatile uint32_t tcpWriteStalls = 0;
volatile uint32_t tcpPartialWrites = 0;
volatile uint32_t tcpMutexTimeouts = 0;
volatile uint32_t tcpMutexWaitMaxMs = 0;
volatile uint32_t tcpMutexWaitSlow = 0;
volatile uint32_t tcpWriteMaxMs = 0;
volatile uint32_t tcpSlowWrites = 0;
volatile uint32_t telemetryGapMaxMs = 0;
volatile uint32_t telemetryGapOverWarn = 0;
volatile uint32_t telemetryGapOverDeadline = 0;
volatile uint32_t telemetryPacketsSent = 0;
volatile uint32_t lastTelemetrySentMs = 0;
volatile uint32_t udpDatagramsSent = 0;
volatile uint32_t udpBytesSent = 0;
volatile uint32_t udpDatagramMaxMs = 0;
volatile uint32_t udpSlowDatagrams = 0;
volatile uint32_t udpFrameMaxMs = 0;
volatile uint32_t thermalFramesSuppressed = 0;
volatile uint32_t thermalFramesDeferred = 0;
volatile uint32_t udpSocketRestarts = 0;
volatile int32_t tcpLastErrno = 0;
volatile int32_t udpLastErrno = 0;
volatile bool tcpLinkHealthy = false;

// 시리얼 A/B 스위치
volatile bool thermalUdpEnabled = true;
volatile bool thermalCaptureEnabled = true;
bool linkDiagnosticsEnabled = true;
bool linkDiagnosticsOnce = false;
bool txLogEnabled = true;

IPAddress rpiHostIp;
bool rpiHostIpValid = false;

// 진단 로그 미러용 소켓. 본 telemetry/thermal 소켓과 완전히 분리되어 있습니다.
WiFiUDP diagUdp;
bool diagUdpStarted = false;
volatile bool diagUdpEnabled = true;
volatile uint32_t diagUdpLinesSent = 0;
volatile uint32_t diagUdpLinesDropped = 0;

// 마지막으로 실제로 전송된 JSON. [tx] 로그와 'j' 명령이 씁니다.
char lastTelemetryJson[1600] = {};
volatile size_t lastTelemetryJsonLength = 0;

// =============================================================================
// 작은 유틸
// =============================================================================
bool scheduleDue(uint32_t now, uint32_t &lastRun, uint32_t period) {
  if (static_cast<uint32_t>(now - lastRun) < period) return false;
  lastRun += period;
  if (static_cast<uint32_t>(now - lastRun) >= period) lastRun = now;
  return true;
}

bool isFresh(uint32_t timestamp, uint32_t now, uint32_t timeout) {
  if (timestamp == 0) return false;
  const int32_t age = static_cast<int32_t>(now - timestamp);
  return age < static_cast<int32_t>(timeout);
}

bool deadlineReached(uint32_t now, uint32_t deadline) {
  return static_cast<int32_t>(now - deadline) >= 0;
}

// 'p' 명령으로 모델 예열을 강제 완료시켰는지.
volatile bool co2ModelPreheatForced = false;

// 값 자체를 막아야 하는 구간 (기본 0 이므로 사실상 항상 false)
bool co2ValueBlocked(uint32_t now) { return now < CO2_VALUE_WARMUP_MS; }

// AI 입력 자격. 이것만 Winsen 3분 규격을 지킵니다.
bool co2ModelPreheatDone(uint32_t now) {
  return co2ModelPreheatForced || now >= CO2_MODEL_PREHEAT_MS;
}

const char *nullReasonText(NullReason reason) {
  switch (reason) {
    case NullReason::OK: return "ok";
    case NullReason::NEVER_SEEN: return "never_seen";
    case NullReason::STALE: return "stale";
    case NullReason::PREHEAT: return "preheat";
    case NullReason::OUT_OF_RANGE: return "out_of_range";
    case NullReason::NOT_FINITE: return "not_finite";
  }
  return "unknown";
}

const char *thermalReadyModeText(ThermalReadyMode mode) {
  switch (mode) {
    case ThermalReadyMode::READY_PIN: return "ready_pin";
    case ThermalReadyMode::I2C_POLL: return "i2c_poll";
    case ThermalReadyMode::CAMERA_ABSENT: return "disabled";
    case ThermalReadyMode::UNKNOWN: return "unknown";
  }
  return "unknown";
}

bool udpHoldoffActive(uint32_t now) {
  return udpHoldoffUntilMs != 0 &&
         static_cast<int32_t>(udpHoldoffUntilMs - now) > 0;
}

void requestUdpHoldoff(uint32_t now, uint32_t durationMs) {
  const uint32_t until = now + durationMs;
  const bool wasActive = udpHoldoffActive(now);
  if (!wasActive || static_cast<int32_t>(until - udpHoldoffUntilMs) > 0) {
    udpHoldoffUntilMs = until;
  }
  if (!wasActive) udpHoldoffEvents = udpHoldoffEvents + 1;
}

// Pi 주소 해석. RPI_HOST 가 IP 리터럴이면 그대로 쓰고, 이름이면 mDNS 로 찾습니다.
//
// Wi-Fi 를 바꿀 때마다 Pi 의 DHCP 주소가 달라지는데, 그때마다 펌웨어를 다시
// 굽는 건 현장에서 감당이 안 됩니다. Pi 에서 avahi-daemon 이 돌고 있으므로
// `sandi.local` 처럼 이름을 넣어두면 주소가 바뀌어도 알아서 따라갑니다.
bool ensureRpiHostIp() {
  if (rpiHostIpValid) return true;
  if (WiFi.status() != WL_CONNECTED) return false;

  // 1) IP 리터럴
  if (rpiHostIp.fromString(RPI_HOST)) {
    rpiHostIpValid = true;
    return true;
  }

  // 2) mDNS. ".local" 접미사는 queryHost 에 넘기기 전에 떼야 합니다.
  char name[64];
  strlcpy(name, RPI_HOST, sizeof(name));
  const size_t length = strlen(name);
  const size_t suffix = strlen(".local");
  if (length > suffix && strcmp(name + length - suffix, ".local") == 0) {
    name[length - suffix] = '\0';
  }
  const IPAddress resolved = MDNS.queryHost(name, 2000);
  if (resolved != IPAddress(static_cast<uint32_t>(0))) {
    rpiHostIp = resolved;
    rpiHostIpValid = true;
    Serial.printf("[mdns] %s -> %s\n", RPI_HOST, rpiHostIp.toString().c_str());
    return true;
  }

  // 3) 일반 DNS (핫스팟이 이름을 배포하는 드문 경우)
  if (WiFi.hostByName(RPI_HOST, rpiHostIp) == 1) {
    rpiHostIpValid = true;
    return true;
  }
  return false;
}

bool isTransientSendErrno(int err) {
  return err == EAGAIN || err == EWOULDBLOCK || err == ENOMEM || err == ENOBUFS;
}

bool udpErrorLooksLikeDeadSocket(int err) {
  return err == EBADF || err == ENOTSOCK || err == ENOTCONN || err == EPIPE;
}

void initializeBootId() {
  uint32_t words[4];
  for (uint8_t index = 0; index < 4; ++index) words[index] = esp_random();
  snprintf(bootId, sizeof(bootId), "%08lx%08lx%08lx%08lx",
           static_cast<unsigned long>(words[0]),
           static_cast<unsigned long>(words[1]),
           static_cast<unsigned long>(words[2]),
           static_cast<unsigned long>(words[3]));
}

// 초기화 전용. 런타임 loop() 에는 delay() 가 없습니다.
void setupWait(uint32_t milliseconds) { vTaskDelay(pdMS_TO_TICKS(milliseconds)); }

void putU16(uint8_t *destination, uint16_t value) {
  destination[0] = static_cast<uint8_t>(value >> 8);
  destination[1] = static_cast<uint8_t>(value);
}

void putU32(uint8_t *destination, uint32_t value) {
  destination[0] = static_cast<uint8_t>(value >> 24);
  destination[1] = static_cast<uint8_t>(value >> 16);
  destination[2] = static_cast<uint8_t>(value >> 8);
  destination[3] = static_cast<uint8_t>(value);
}

// =============================================================================
// I2C / Thermal 레지스터
// =============================================================================
bool i2cPresent(uint8_t address) {
  Wire.beginTransmission(address);
  return Wire.endTransmission() == 0;
}

bool thermalWriteRegister(uint8_t reg, uint8_t value) {
  if (thermalAddress == 0) return false;
  Wire.beginTransmission(thermalAddress);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool thermalReadRegister(uint8_t reg, uint8_t &value) {
  if (thermalAddress == 0) return false;
  Wire.beginTransmission(thermalAddress);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(thermalAddress, static_cast<uint8_t>(1)) != 1) return false;
  value = Wire.read();
  return true;
}

void scanI2cBus() {
  uint8_t found = 0;
  Serial.print("[i2c] scan:");
  for (uint8_t address = 1; address < 127; ++address) {
    if (i2cPresent(address)) {
      Serial.printf(" 0x%02X", static_cast<unsigned>(address));
      ++found;
    }
  }
  if (found == 0) Serial.print(" (none)");
  Serial.printf("  devices=%u\n", static_cast<unsigned>(found));
  if (found == 0) {
    Serial.println(
        "[i2c] WARNING: I2C 에 아무것도 없습니다. SDA=21 SCL=22 배선, 풀업, "
        "열화상 모듈 전원(3.3V)을 확인하세요. 이 상태면 열화상은 절대 안 나옵니다.");
  }
}

// 한 프레임(헤더 80 워드 + 픽셀 4960 워드)을 SPI 로 읽어 thermalCapture 에 넣습니다.
// READY 핀 판별에서도 그대로 재사용합니다. MI48 의 READY 는 프레임이 준비되면
// HIGH 로 래치되고 SPI 로 읽어갈 때까지 내려가지 않기 때문에, "읽어보고 내려가는가"가
// 핀이 살아 있는지 확인하는 유일하게 확실한 방법입니다.
void readThermalFrameRaw() {
  thermalSpi.beginTransaction(SPISettings(THERMAL_SPI_HZ, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_THERMAL_CS, LOW);
  delayMicroseconds(100);
  // MI48xx 는 워드를 MSB first 로 냅니다. 바이트 단위로 읽어야 호스트
  // 엔디언 모호성이 사라집니다.
  for (size_t i = 0; i < THERMAL_CAPTURE_WORDS; ++i) {
    const uint8_t highByte = thermalSpi.transfer(0x00);
    const uint8_t lowByte = thermalSpi.transfer(0x00);
    thermalCapture[i] = (static_cast<uint16_t>(highByte) << 8) | lowByte;
  }
  delayMicroseconds(100);
  digitalWrite(PIN_THERMAL_CS, HIGH);
  thermalSpi.endTransaction();
}

// READY 핀이 진짜로 토글하는지 관찰합니다. 붕 떠 있거나 계속 HIGH 인 배선을
// "데이터 준비됨"으로 오독하면 루프마다 SPI 를 때려서 쓰레기 프레임이 쏟아집니다.
ThermalReadyMode probeThermalReadyPin() {
  // 1단계: 관찰. rise(LOW->HIGH)를 한 번이라도 보면 핀이 살아 있는 게 확정입니다.
  uint32_t highSamples = 0;
  uint32_t lowSamples = 0;
  uint32_t rises = 0;
  int previous = digitalRead(PIN_THERMAL_READY);
  const uint32_t started = millis();
  while (static_cast<uint32_t>(millis() - started) < THERMAL_READY_PROBE_MS) {
    const int level = digitalRead(PIN_THERMAL_READY);
    if (level == HIGH) ++highSamples; else ++lowSamples;
    if (level == HIGH && previous == LOW) ++rises;
    previous = level;
    vTaskDelay(pdMS_TO_TICKS(1));
  }
  Serial.printf(
      "[thermal] READY probe phase1: high=%lu low=%lu rises=%lu window_ms=%lu\n",
      static_cast<unsigned long>(highSamples),
      static_cast<unsigned long>(lowSamples),
      static_cast<unsigned long>(rises),
      static_cast<unsigned long>(THERMAL_READY_PROBE_MS));

  if (rises > 0) {
    Serial.println("[thermal] READY rise 관측 -> ready_pin 모드");
    return ThermalReadyMode::READY_PIN;
  }
  if (highSamples == 0) {
    Serial.println(
        "[thermal] WARNING: READY 가 관찰 구간 내내 LOW 입니다. 프레임이 생성되지 "
        "않거나 READY(GPIO26) 배선이 끊겼습니다. I2C STATUS 폴링으로 전환합니다.");
    return ThermalReadyMode::I2C_POLL;
  }

  // 2단계: 내내 HIGH. 이건 두 가지 중 하나입니다.
  //   (a) 정상 - 관찰 시작 전에 이미 프레임이 준비되어 래치된 상태.
  //       MI48 의 READY 는 SPI 로 읽어가기 전까지 내려가지 않으므로,
  //       관찰만 해서는 절대 rise 를 볼 수 없습니다.
  //   (b) 고장 - 핀 미연결/플로팅으로 항상 HIGH 로 읽힘.
  // 더미 프레임을 한 장 읽어 래치를 소거해 보면 둘이 갈립니다.
  Serial.println(
      "[thermal] READY probe phase2: 내내 HIGH -> 더미 프레임을 읽어 래치가 "
      "소거되는지 확인합니다");
  readThermalFrameRaw();
  setupWait(20);
  if (digitalRead(PIN_THERMAL_READY) == LOW) {
    Serial.println(
        "[thermal] 더미 read 후 READY 가 LOW 로 떨어짐 = 핀 정상 -> ready_pin 모드");
    return ThermalReadyMode::READY_PIN;
  }
  Serial.println(
      "[thermal] WARNING: 더미 read 후에도 READY 가 HIGH 입니다(핀 미연결/플로팅). "
      "I2C STATUS 폴링으로 전환합니다. 열화상 자체는 폴링으로 계속 동작합니다.");
  return ThermalReadyMode::I2C_POLL;
}

void initializeThermalCamera() {
  if (i2cPresent(THERMAL_ADDRESS_A)) {
    thermalAddress = THERMAL_ADDRESS_A;
  } else if (i2cPresent(THERMAL_ADDRESS_B)) {
    thermalAddress = THERMAL_ADDRESS_B;
  } else {
    Serial.println("[thermal] ERROR: I2C 0x40/0x41 에 열화상 모듈이 없습니다");
    thermalReadyMode = ThermalReadyMode::CAMERA_ABSENT;
    return;
  }

  digitalWrite(PIN_THERMAL_RESET, LOW);
  delayMicroseconds(100);
  digitalWrite(PIN_THERMAL_RESET, HIGH);
  setupWait(100);

  uint8_t evkTest = 0;
  if (!thermalReadRegister(REG_EVK_TEST, evkTest)) {
    Serial.println("[thermal] ERROR: 레지스터 읽기 실패");
    thermalReadyMode = ThermalReadyMode::CAMERA_ABSENT;
    return;
  }

  // 브리지가 아닌 MI48 변종은 명시적 power-up 이 필요합니다.
  if (evkTest != 0xFF) {
    if (!thermalWriteRegister(REG_SENSOR_POWERUP, 0x13)) {
      Serial.println("[thermal] ERROR: power-up 명령 실패");
      thermalReadyMode = ThermalReadyMode::CAMERA_ABSENT;
      return;
    }
    setupWait(100);
  }

  const uint32_t bootStarted = millis();
  uint8_t status = STATUS_BOOTING;
  while (static_cast<uint32_t>(millis() - bootStarted) < 3000) {
    if (!thermalReadRegister(REG_STATUS, status)) {
      Serial.println("[thermal] ERROR: status 읽기 실패");
      thermalReadyMode = ThermalReadyMode::CAMERA_ABSENT;
      return;
    }
    if ((status & STATUS_BOOTING) == 0) break;
    setupWait(25);
  }
  if (status & STATUS_BOOTING) {
    Serial.println("[thermal] ERROR: boot timeout");
    thermalReadyMode = ThermalReadyMode::CAMERA_ABSENT;
    return;
  }

  uint8_t fw1 = 0, fw2 = 0, sensorType = 0;
  thermalReadRegister(REG_FW_VERSION_1, fw1);
  thermalReadRegister(REG_FW_VERSION_2, fw2);
  thermalReadRegister(REG_SENSOR_TYPE, sensorType);

  thermalWriteRegister(REG_FRAME_MODE, 0x00);
  setupWait(30);
  if (!thermalWriteRegister(REG_FRAME_RATE, THERMAL_FRAME_RATE_DIVIDER) ||
      !thermalWriteRegister(REG_FRAME_MODE, MODE_CONTINUOUS)) {
    Serial.println("[thermal] ERROR: continuous stream 시작 실패");
    thermalReadyMode = ThermalReadyMode::CAMERA_ABSENT;
    return;
  }

  thermalStarted = true;
  Serial.printf(
      "[thermal] ready: addr=0x%02X type=%u fw=%u.%u.%u divider=%u "
      "(target ~%.2f fps) strict_validation=%d\n",
      static_cast<unsigned>(thermalAddress), static_cast<unsigned>(sensorType),
      static_cast<unsigned>((fw1 >> 4) & 0x0F), static_cast<unsigned>(fw1 & 0x0F),
      static_cast<unsigned>(fw2), static_cast<unsigned>(THERMAL_FRAME_RATE_DIVIDER),
      25.0f / static_cast<float>(THERMAL_FRAME_RATE_DIVIDER),
      THERMAL_STRICT_VALIDATION ? 1 : 0);

  thermalReadyMode = probeThermalReadyPin();
}

// =============================================================================
// Thermal 캡처
// =============================================================================
bool thermalDataReady(uint32_t now) {
  if (thermalReadyMode == ThermalReadyMode::READY_PIN) {
    if (digitalRead(PIN_THERMAL_READY) == HIGH) {
      ++thermalReadyByPin;
      return true;
    }
    return false;
  }
  if (thermalReadyMode != ThermalReadyMode::I2C_POLL) return false;

  // ~1 fps 스트림에서 25 ms 폴링이면 충분합니다.
  if (static_cast<uint32_t>(now - lastThermalStatusPollMs) < 25) return false;
  lastThermalStatusPollMs = now;
  uint8_t status = 0;
  if (!thermalReadRegister(REG_STATUS, status)) {
    ++thermalStatusQueryFailures;
    return false;
  }
  if ((status & STATUS_DATA_READY) == 0) return false;
  ++thermalReadyByI2c;
  return true;
}

// 헤더 워드에서 픽셀 min/max 와 일치하는 인덱스를 찾습니다.
// v2 는 이 배치를 5/6 으로 가정하고 틀리면 전 프레임을 버렸습니다.
void probeThermalHeaderLayout(uint16_t actualMin, uint16_t actualMax) {
  if (thermalHeaderLayoutResolved || thermalHeaderLayoutGiveUp) return;
  int8_t minIndex = -1;
  int8_t maxIndex = -1;
  for (int8_t index = 0; index < 16; ++index) {
    const uint16_t word = thermalCapture[index];
    if (minIndex < 0 && word == actualMin) minIndex = index;
    if (maxIndex < 0 && word == actualMax) maxIndex = index;
  }
  ++thermalHeaderProbes;
  if (minIndex >= 0 && maxIndex >= 0 && minIndex != maxIndex) {
    if (thermalHeaderMinIndex < 0) {
      thermalHeaderMinIndex = minIndex;
      thermalHeaderMaxIndex = maxIndex;
    } else if (thermalHeaderMinIndex == minIndex &&
               thermalHeaderMaxIndex == maxIndex) {
      // 같은 배치가 두 프레임 연속으로 맞으면 확정합니다.
      thermalHeaderLayoutResolved = true;
      Serial.printf(
          "[thermal] header layout resolved: min_index=%d max_index=%d "
          "(probe_frames=%u)\n",
          static_cast<int>(thermalHeaderMinIndex),
          static_cast<int>(thermalHeaderMaxIndex),
          static_cast<unsigned>(thermalHeaderProbes));
      return;
    } else {
      // 불일치. 처음부터 다시.
      thermalHeaderMinIndex = minIndex;
      thermalHeaderMaxIndex = maxIndex;
    }
  }
  if (thermalHeaderProbes >= THERMAL_HEADER_PROBE_FRAMES) {
    thermalHeaderLayoutGiveUp = true;
    Serial.printf(
        "[thermal] header layout UNRESOLVED after %u frames -> 헤더 검증을 "
        "끄고 계속 전송합니다. 픽셀 데이터 자체는 정상일 수 있습니다. "
        "hdr[0..7]=%u,%u,%u,%u,%u,%u,%u,%u\n",
        static_cast<unsigned>(thermalHeaderProbes),
        static_cast<unsigned>(thermalCapture[0]),
        static_cast<unsigned>(thermalCapture[1]),
        static_cast<unsigned>(thermalCapture[2]),
        static_cast<unsigned>(thermalCapture[3]),
        static_cast<unsigned>(thermalCapture[4]),
        static_cast<unsigned>(thermalCapture[5]),
        static_cast<unsigned>(thermalCapture[6]),
        static_cast<unsigned>(thermalCapture[7]));
  }
}

void captureThermalIfReady(uint32_t now) {
  if (!thermalStarted || !thermalCaptureEnabled) return;
  if (!thermalDataReady(now)) return;

  ++thermalCaptureAttempts;
  const uint32_t captureStartedMs = millis();
  readThermalFrameRaw();
  const uint32_t captureMs = static_cast<uint32_t>(millis() - captureStartedMs);

  // 런타임 안전장치. 정상 READY 래치는 프레임을 읽어가면 반드시 LOW 로 떨어집니다.
  // 읽은 직후에도 계속 HIGH 라면 부팅 probe 가 놓친 플로팅 핀이라는 뜻이고,
  // 그대로 두면 루프마다(초당 수만 번) SPI 를 때려 쓰레기 프레임을 쏟아냅니다.
  // 스스로 I2C 폴링으로 내려갑니다.
  if (thermalReadyMode == ThermalReadyMode::READY_PIN) {
    if (digitalRead(PIN_THERMAL_READY) == HIGH) {
      ++thermalReadyStuckAfterRead;
      if (thermalReadyStuckAfterRead >= 5) {
        thermalReadyMode = ThermalReadyMode::I2C_POLL;
        ++thermalReadyDemotions;
        Serial.printf(
            "[thermal] WARNING: 프레임을 읽은 뒤에도 READY 가 %lu회 연속 HIGH "
            "입니다 -> 핀을 믿을 수 없어 i2c_poll 로 자동 전환합니다 "
            "(demotions=%lu)\n",
            static_cast<unsigned long>(thermalReadyStuckAfterRead),
            static_cast<unsigned long>(thermalReadyDemotions));
      }
    } else {
      thermalReadyStuckAfterRead = 0;
    }
  }
  if (captureMs > thermalCaptureMaxMs) thermalCaptureMaxMs = captureMs;

  for (uint8_t i = 0; i < 16; ++i) thermalLastHeader[i] = thermalCapture[i];

  ThermalTxFrame &frame = thermalProducerFrame;
  frame.uptimeMs = millis();
  frame.minimumRaw = UINT16_MAX;
  frame.maximumRaw = 0;
  for (size_t i = 0; i < THERMAL_PIXEL_COUNT; ++i) {
    const uint16_t raw = thermalCapture[THERMAL_HEADER_WORDS + i];
    frame.pixels[i] = raw;
    if (raw < frame.minimumRaw) frame.minimumRaw = raw;
    if (raw > frame.maximumRaw) frame.maximumRaw = raw;
  }

  // 전 픽셀이 같은 값이면 SPI 가 아무것도 못 읽고 있다는 뜻입니다
  // (CS/MISO 미연결이면 0x0000 또는 0xFFFF 로 꽉 찹니다).
  // 이건 프레임을 버릴 이유가 아니라, 사람에게 알려야 할 배선 신호입니다.
  if (frame.minimumRaw == frame.maximumRaw) {
    ++thermalFlatFrames;
    if (thermalFlatFrames <= 3 || thermalFlatFrames % 50 == 0) {
      Serial.printf(
          "[thermal] WARNING: flat frame (모든 픽셀=%u, count=%lu). "
          "SPI MISO=19 / CS=27 / SCLK=18 배선과 CS 타이밍을 확인하세요.\n",
          static_cast<unsigned>(frame.minimumRaw),
          static_cast<unsigned long>(thermalFlatFrames));
    }
  }

  probeThermalHeaderLayout(frame.minimumRaw, frame.maximumRaw);

  bool headerMatches = true;
  if (thermalHeaderLayoutResolved) {
    headerMatches =
        thermalCapture[thermalHeaderMinIndex] == frame.minimumRaw &&
        thermalCapture[thermalHeaderMaxIndex] == frame.maximumRaw;
    if (!headerMatches) {
      ++thermalHeaderMismatches;
      if (thermalHeaderMismatches <= 3 || thermalHeaderMismatches % 50 == 0) {
        Serial.printf(
            "[thermal] header mismatch: hdr_min=%u hdr_max=%u calc=%u..%u "
            "mismatches=%lu strict=%d\n",
            static_cast<unsigned>(thermalCapture[thermalHeaderMinIndex]),
            static_cast<unsigned>(thermalCapture[thermalHeaderMaxIndex]),
            static_cast<unsigned>(frame.minimumRaw),
            static_cast<unsigned>(frame.maximumRaw),
            static_cast<unsigned long>(thermalHeaderMismatches),
            THERMAL_STRICT_VALIDATION ? 1 : 0);
      }
    }
  }

  if (!headerMatches && THERMAL_STRICT_VALIDATION) {
    ++thermalStrictDrops;
    return;
  }

  frame.frameSequence = ++thermalSequence;
  // 큐 길이 1. 혼잡할 때는 못 보낸 옛 프레임을 최신 프레임이 덮습니다.
  xQueueOverwrite(thermalQueue, &frame);
}

// =============================================================================
// MH-Z19B (UART1)
// =============================================================================
uint8_t mhz19Checksum(const uint8_t *frame) {
  uint8_t sum = 0;
  for (uint8_t index = 1; index <= 7; ++index) sum = static_cast<uint8_t>(sum + frame[index]);
  return static_cast<uint8_t>(~sum + 1);
}

void resetMhz19Rx() {
  mhz19RxLength = 0;
  while (mhz19Serial.available() > 0) (void)mhz19Serial.read();
}

void sendMhz19ReadCommand(uint32_t now) {
  resetMhz19Rx();
  mhz19Serial.write(MHZ19_READ_CMD, sizeof(MHZ19_READ_CMD));
  mhz19Serial.flush();
  mhz19Txn = Mhz19Txn::AWAIT_RESPONSE;
  mhz19RequestSentMs = now;
  ++co2RequestsSent;
}

void acceptMhz19Sample(uint32_t now, uint16_t ppm) {
  co2LastUartPpm = ppm;
  ++co2AcceptedSamples;

  if (co2ValueBlocked(now)) return;  // 기본 0 이라 즉시 통과합니다
  if (ppm < CO2_PPM_MIN_ACCEPTED || ppm > CO2_PPM_MAX_ACCEPTED) {
    ++co2RangeRejects;
    if (co2RangeRejects <= 5 || co2RangeRejects % 50 == 0) {
      Serial.printf(
          "[co2] rejected out-of-range ppm=%u (accept %u..%u) rejects=%lu\n",
          static_cast<unsigned>(ppm), static_cast<unsigned>(CO2_PPM_MIN_ACCEPTED),
          static_cast<unsigned>(CO2_PPM_MAX_ACCEPTED),
          static_cast<unsigned long>(co2RangeRejects));
    }
    return;
  }

  co2Ppm = ppm;
  lastCo2Ms = now;
  ++co2MeasurementEventId;
  if (co2MeasurementEventId == 0) ++co2MeasurementEventId;  // 0 은 "무효" 예약값
  co2MeasurementMonotonicMs = now;
  co2MeasurementEventValid = true;
}

// 링버퍼에서 0xFF 0x86 헤더를 찾아 재동기화합니다. v2 는 이걸 안 해서 한 번
// 바이트가 밀리면 영원히 checksum 실패만 셌습니다.
bool tryConsumeMhz19Frame(uint32_t now) {
  while (mhz19Serial.available() > 0 && mhz19RxLength < sizeof(mhz19RxBuffer)) {
    mhz19RxBuffer[mhz19RxLength++] = static_cast<uint8_t>(mhz19Serial.read());
  }
  if (mhz19RxLength < 9) return false;

  for (uint8_t start = 0; start + 9 <= mhz19RxLength; ++start) {
    if (mhz19RxBuffer[start] != 0xFF || mhz19RxBuffer[start + 1] != 0x86) continue;
    const uint8_t *frame = mhz19RxBuffer + start;
    if (mhz19Checksum(frame) != frame[8]) {
      ++co2ChecksumFailures;
      if (co2ChecksumFailures <= 5 || co2ChecksumFailures % 50 == 0) {
        Serial.printf(
            "[co2] checksum fail: %02X %02X %02X %02X %02X %02X %02X %02X %02X "
            "(calc=%02X) fails=%lu\n",
            frame[0], frame[1], frame[2], frame[3], frame[4], frame[5], frame[6],
            frame[7], frame[8], mhz19Checksum(frame),
            static_cast<unsigned long>(co2ChecksumFailures));
      }
      mhz19RxLength = 0;
      return true;
    }
    if (start > 0) {
      ++co2ResyncEvents;
      if (co2ResyncEvents <= 5) {
        Serial.printf("[co2] resynced past %u stray byte(s)\n",
                      static_cast<unsigned>(start));
      }
    }
    const uint16_t ppm = (static_cast<uint16_t>(frame[2]) << 8) | frame[3];
    acceptMhz19Sample(now, ppm);
    mhz19RxLength = 0;
    return true;
  }

  // 9바이트 이상 모였는데 헤더를 못 찾음 = 배선/보레이트 문제.
  ++co2HeaderFailures;
  if (co2HeaderFailures <= 5 || co2HeaderFailures % 50 == 0) {
    Serial.printf(
        "[co2] no 0xFF 0x86 header in %u byte(s): %02X %02X %02X %02X ... "
        "fails=%lu  -> RX=%d/TX=%d 교차 배선과 9600 8N1, 5V 전원을 확인하세요\n",
        static_cast<unsigned>(mhz19RxLength), mhz19RxBuffer[0], mhz19RxBuffer[1],
        mhz19RxBuffer[2], mhz19RxBuffer[3],
        static_cast<unsigned long>(co2HeaderFailures), PIN_MHZ19_RX, PIN_MHZ19_TX);
  }
  mhz19RxLength = 0;
  return true;
}

void pollCo2(uint32_t now) {
  if (mhz19Txn == Mhz19Txn::IDLE) {
    if (!scheduleDue(now, lastCo2PollMs, CO2_UART_SAMPLE_PERIOD_MS)) return;
    sendMhz19ReadCommand(now);
    return;
  }

  if (tryConsumeMhz19Frame(now)) {
    mhz19Txn = Mhz19Txn::IDLE;
    return;
  }

  if (deadlineReached(now, mhz19RequestSentMs + CO2_UART_RESPONSE_TIMEOUT_MS)) {
    if (mhz19RxLength > 0) {
      ++co2ShortFrameFailures;
      if (co2ShortFrameFailures <= 5 || co2ShortFrameFailures % 50 == 0) {
        Serial.printf("[co2] short frame: %u/9 bytes in %lu ms (fails=%lu)\n",
                      static_cast<unsigned>(mhz19RxLength),
                      static_cast<unsigned long>(CO2_UART_RESPONSE_TIMEOUT_MS),
                      static_cast<unsigned long>(co2ShortFrameFailures));
      }
    } else {
      ++co2TimeoutFailures;
      if (co2TimeoutFailures <= 5 || co2TimeoutFailures % 50 == 0) {
        Serial.printf(
            "[co2] timeout: 0 bytes in %lu ms (timeouts=%lu) -> MH-Z19B TX 가 "
            "GPIO%d 에 물려 있는지, 센서가 5V 로 켜졌는지 확인하세요\n",
            static_cast<unsigned long>(CO2_UART_RESPONSE_TIMEOUT_MS),
            static_cast<unsigned long>(co2TimeoutFailures), PIN_MHZ19_RX);
      }
    }
    resetMhz19Rx();
    mhz19Txn = Mhz19Txn::IDLE;
  }
}

// =============================================================================
// MR60BHA2 (UART2)
// =============================================================================
void pollMmWave(uint32_t now) {
  // timeout=0 은 이미 버퍼에 있는 바이트만 논블로킹으로 소비합니다.
  // 여러 프레임을 연속으로 비워야 나중 SPI 버스트가 Seeed 정적 파서 안에
  // 반쪽 SOF 를 남기지 않습니다. 빈 UART 에서 update() 가 false 인 것은
  // 정상 idle 이지 고장이 아닙니다 (v2 는 이걸 miss 로 세서 루프 주파수만큼
  // 카운터가 올라 크래시처럼 보였습니다).
  bool parsed = false;
  bool gotBreath = false;
  bool gotHeart = false;
  for (uint8_t n = 0; n < 16; ++n) {
    if (!mmWave.update(0)) break;
    parsed = true;
    ++mmWaveUpdateSuccesses;
    lastMmWaveUpdateMs = now;

    float nextTotal = NAN, nextBreath = NAN, nextHeart = NAN;
    if (mmWave.getHeartBreathPhases(nextTotal, nextBreath, nextHeart) &&
        isfinite(nextTotal) && isfinite(nextBreath) && isfinite(nextHeart)) {
      totalPhase = nextTotal;
      breathPhase = nextBreath;
      heartPhase = nextHeart;
      lastPhaseMs = millis();
      phaseSamplePresent = true;
      ++phaseSequence;
    }

    float value = 0.0f;
    if (mmWave.getBreathRate(value) && isfinite(value)) {
      respirationRate = value;
      lastRespirationMs = now;
      ++mmWaveBreathSamples;
      gotBreath = true;
    }
    if (mmWave.getHeartRate(value) && isfinite(value)) {
      heartRate = value;
      lastHeartMs = now;
      ++mmWaveHeartSamples;
      gotHeart = true;
    }

    // MR60 가 스스로 정규화한 재실 boolean 을 그대로 씁니다. 호흡수에서
    // 재실을 추론하거나 다수결 스무딩을 하지 않습니다 (와이어 계약이
    // human_detected_raw 하나뿐).
    bool presenceValue = false;
    if (mmWave.takePresence(presenceValue)) {
      humanDetectedRaw = presenceValue;
      lastPresenceMs = now;
      ++mmWavePresenceReports;
    }
  }
  if (!parsed && mmWaveSerial.available() > 0) ++mmWaveUpdateMisses;

  if (gotBreath || gotHeart) {
    static uint32_t lastSampleLogMs = 0;
    if (lastSampleLogMs == 0 ||
        static_cast<uint32_t>(now - lastSampleLogMs) >= 2000) {
      lastSampleLogMs = now;
      Serial.printf(
          "[mmw] breath=%.2f heart=%.2f presence=%s phase=%.4f phase_seq=%lu "
          "frames=%lu uart_pending=%u\n",
          respirationRate, heartRate,
          lastPresenceMs == 0 ? "unknown" : (humanDetectedRaw ? "true" : "false"),
          breathPhase, static_cast<unsigned long>(phaseSequence),
          static_cast<unsigned long>(mmWave.framesParsed()),
          static_cast<unsigned>(mmWaveSerial.available()));
    }
  }
}

// =============================================================================
// Telemetry 스냅샷 발행
// =============================================================================
NullReason floatReason(bool fresh, uint32_t lastMs, float value) {
  if (lastMs == 0) return NullReason::NEVER_SEEN;
  if (!fresh) return NullReason::STALE;
  if (!isfinite(value)) return NullReason::NOT_FINITE;
  return NullReason::OK;
}

void publishTelemetrySnapshot(uint32_t now) {
  if (!scheduleDue(now, lastTelemetryMs, TELEMETRY_PERIOD_MS)) return;

  TelemetrySnapshot snapshot{};
  snapshot.sequence = ++telemetrySequence;
  snapshot.uptimeMs = now;
  snapshot.respirationRate = respirationRate;
  snapshot.heartRate = heartRate;
  snapshot.co2Ppm = co2Ppm;
  snapshot.pirMotion = pirMotion;
  snapshot.respirationValid =
      isFresh(lastRespirationMs, now, MMWAVE_STALE_MS) && isfinite(respirationRate);
  snapshot.heartValid =
      isFresh(lastHeartMs, now, MMWAVE_STALE_MS) && isfinite(heartRate);
  snapshot.respReason =
      floatReason(isFresh(lastRespirationMs, now, MMWAVE_STALE_MS),
                  lastRespirationMs, respirationRate);
  snapshot.heartReason = floatReason(isFresh(lastHeartMs, now, MMWAVE_STALE_MS),
                                     lastHeartMs, heartRate);

  // co2_preheat 은 "AI 입력 자격이 아직 없다"는 뜻으로만 남깁니다.
  // 표시값은 이것과 무관하게 즉시 나갑니다.
  snapshot.co2Preheat = !co2ModelPreheatDone(now);
  // valid.co2 는 "마지막 성공이 stale 한도 안"이라는 뜻이지 "새 이벤트"가 아닙니다.
  snapshot.co2Valid =
      !co2ValueBlocked(now) && isFresh(lastCo2Ms, now, CO2_STALE_MS);
  if (co2ValueBlocked(now)) {
    snapshot.co2Reason = NullReason::PREHEAT;
  } else if (lastCo2Ms == 0) {
    snapshot.co2Reason = NullReason::NEVER_SEEN;
  } else if (!snapshot.co2Valid) {
    snapshot.co2Reason = NullReason::STALE;
  } else {
    snapshot.co2Reason = NullReason::OK;
  }

  // 이벤트 정체성은 대응하는 UART 샘플이 신선한 동안만 유효합니다. stale/예열이면
  // 프로토콜이 요구하는 0/0/false 로 fail-closed 합니다. 같은 event_id 가 이후
  // 스냅샷에 다시 실리는 것은 캐시 재전송이고, Pi slope 는 packet seq 가 아니라
  // event_id 로 중복을 걸러냅니다.
  // 이벤트 정체성은 AI 이력의 키입니다. 모델 예열 전 샘플이 H150 창에 섞이면
  // 안 되므로 여기서는 계속 규격을 지킵니다.
  const bool co2EventFresh = snapshot.co2Valid && co2MeasurementEventValid &&
                             co2ModelPreheatDone(now);
  snapshot.co2MeasurementEventId = co2EventFresh ? co2MeasurementEventId : 0;
  snapshot.co2MeasurementMonotonicMs = co2EventFresh ? co2MeasurementMonotonicMs : 0;
  snapshot.co2MeasurementEventValid = co2EventFresh;

  // isFresh() 가 lastPresenceMs==0 도 걸러내므로, 레이더가 한 번도 재실
  // 리포트를 안 보낸 노드는 false 가 아니라 null 을 냅니다. Pi 의 presence
  // 게이트는 false 를 "빈 방"으로 읽기 때문에 이 구분이 필수입니다.
  snapshot.humanDetectedRaw = humanDetectedRaw;
  snapshot.humanDetectedKnown = isFresh(lastPresenceMs, now, PRESENCE_MAX_AGE_MS);

  snapshot.phaseSamplePresent = phaseSamplePresent;
  snapshot.totalPhase = totalPhase;
  snapshot.breathPhase = breathPhase;
  snapshot.heartPhase = heartPhase;
  snapshot.phaseTimestampMs = phaseSamplePresent ? lastPhaseMs : 0;
  snapshot.phaseSequence = phaseSequence;

  xQueueOverwrite(telemetryQueue, &snapshot);
}

// =============================================================================
// TCP 전송
// =============================================================================
void makePacketHeader(uint8_t *header, uint8_t type, uint32_t sequence,
                      uint32_t payloadLength) {
  memcpy(header, "SNST", 4);
  header[4] = PROTOCOL_VERSION;
  header[5] = type;
  putU16(header + 6, 0);
  putU32(header + 8, sequence);
  putU32(header + 12, payloadLength);
}

// 네트워크 태스크에서만 돕니다. Arduino-ESP32 3.x 의 NetworkClient::write() 는
// 내부 select 대기 때문에 한 번에 ~10 초까지 잡혀 있을 수 있고, 그러면 Pi 의
// 수신 데드라인(5 s)을 넘겨 소켓이 먼저 닫힙니다. 그래서 여기서는
// lwip_send(MSG_DONTWAIT) 를 직접 돌리고 TCP_WRITE_DEADLINE_MS 안에 실패시킵니다.
bool writeAll(WiFiClient &client, const uint8_t *data, size_t length,
              TcpWriteReport &report) {
  report = TcpWriteReport{};
  const int sock = client.fd();
  if (sock < 0) {
    report.connectedAtEnd = false;
    report.lastErrno = EBADF;
    return false;
  }

  size_t sent = 0;
  const uint32_t startedMs = millis();
  uint32_t lastProgress = startedMs;

  while (sent < length) {
    const uint32_t elapsedMs = static_cast<uint32_t>(millis() - startedMs);
    if (elapsedMs > TCP_WRITE_DEADLINE_MS) {
      report.bytesWritten = sent;
      report.elapsedMs = elapsedMs;
      if (report.lastErrno == 0) report.lastErrno = ETIMEDOUT;
      report.connectedAtEnd = client.connected();
      return false;
    }
    if (!client.connected()) {
      report.bytesWritten = sent;
      report.elapsedMs = elapsedMs;
      report.connectedAtEnd = false;
      if (report.lastErrno == 0) report.lastErrno = ENOTCONN;
      return false;
    }

    const size_t remaining = length - sent;
    errno = 0;
    const int written = lwip_send(sock, data + sent, remaining, MSG_DONTWAIT);
    if (written > 0) {
      if (static_cast<size_t>(written) < remaining) ++report.partialWrites;
      sent += static_cast<size_t>(written);
      lastProgress = millis();
    } else {
      ++report.zeroWrites;
      const int err = written < 0 ? errno : ENOTCONN;
      report.lastErrno = err;
      const uint32_t stallMs = static_cast<uint32_t>(millis() - lastProgress);
      if (stallMs > report.longestStallMs) report.longestStallMs = stallMs;
      if (written == 0 || !isTransientSendErrno(err)) {
        report.bytesWritten = sent;
        report.elapsedMs = static_cast<uint32_t>(millis() - startedMs);
        report.connectedAtEnd = client.connected();
        return false;
      }
      vTaskDelay(pdMS_TO_TICKS(2));
    }
  }

  report.bytesWritten = sent;
  report.elapsedMs = static_cast<uint32_t>(millis() - startedMs);
  report.connectedAtEnd = true;
  return true;
}

bool beginTcpCritical(uint32_t &waitMs) {
  const uint32_t startedMs = millis();
  xEventGroupSetBits(networkEvents, TCP_CRITICAL_BIT);
  const bool acquired =
      xSemaphoreTake(networkTxMutex, pdMS_TO_TICKS(TCP_MUTEX_MAX_WAIT_MS)) == pdTRUE;
  waitMs = static_cast<uint32_t>(millis() - startedMs);
  if (waitMs > tcpMutexWaitMaxMs) tcpMutexWaitMaxMs = waitMs;
  if (waitMs >= TCP_MUTEX_WARN_MS) tcpMutexWaitSlow = tcpMutexWaitSlow + 1;
  if (acquired) return true;
  xEventGroupClearBits(networkEvents, TCP_CRITICAL_BIT);
  return false;
}

void endTcpCritical() {
  xSemaphoreGive(networkTxMutex);
  xEventGroupClearBits(networkEvents, TCP_CRITICAL_BIT);
}

void formatNullableFloat(char *output, size_t outputSize, bool valid, float value) {
  if (valid && isfinite(value)) {
    const int written = snprintf(output, outputSize, "%.2f", value);
    // 잘린 숫자는 문법상 JSON 이지만 크기가 틀립니다. null 로 fail-closed.
    if (written > 0 && static_cast<size_t>(written) < outputSize) return;
  }
  strlcpy(output, "null", outputSize);
}

void formatNullablePhase(char *output, size_t outputSize, bool valid, float value) {
  if (valid && isfinite(value)) {
    const int written = snprintf(output, outputSize, "%.6f", value);
    if (written > 0 && static_cast<size_t>(written) < outputSize) return;
  }
  strlcpy(output, "null", outputSize);
}

void formatNullableU32(char *output, size_t outputSize, bool valid, uint32_t value) {
  if (valid) {
    const int written =
        snprintf(output, outputSize, "%lu", static_cast<unsigned long>(value));
    if (written > 0 && static_cast<size_t>(written) < outputSize) return;
  }
  strlcpy(output, "null", outputSize);
}

// JSON 을 만들어 lastTelemetryJson 에 남기고 소켓으로 보냅니다.
bool sendTelemetry(WiFiClient &client, const TelemetrySnapshot &snapshot,
                   size_t &payloadLength, TcpWriteReport &report) {
  payloadLength = 0;
  report = TcpWriteReport{};

  char respiration[20], heart[20], co2[12];
  formatNullableFloat(respiration, sizeof(respiration), snapshot.respirationValid,
                      snapshot.respirationRate);
  formatNullableFloat(heart, sizeof(heart), snapshot.heartValid, snapshot.heartRate);
  if (snapshot.co2Valid) {
    const int written =
        snprintf(co2, sizeof(co2), "%u", static_cast<unsigned>(snapshot.co2Ppm));
    if (written <= 0 || static_cast<size_t>(written) >= sizeof(co2)) {
      strlcpy(co2, "null", sizeof(co2));
    }
  } else {
    strlcpy(co2, "null", sizeof(co2));
  }

  const char *humanDetectedText =
      snapshot.humanDetectedKnown ? (snapshot.humanDetectedRaw ? "true" : "false")
                                  : "null";

  char totalPhaseText[32], breathPhaseText[32], heartPhaseText[32];
  char breathRateRawText[20], phaseAgeText[20], phaseTimestampText[20];
  char phaseSequenceText[20];
  const uint32_t sendNow = millis();
  const uint32_t phaseAgeMs =
      snapshot.phaseSamplePresent
          ? static_cast<uint32_t>(sendNow - snapshot.phaseTimestampMs)
          : 0;
  const bool phaseFresh =
      snapshot.phaseSamplePresent && phaseAgeMs < PHASE_MAX_AGE_MS;
  formatNullablePhase(totalPhaseText, sizeof(totalPhaseText), phaseFresh,
                      snapshot.totalPhase);
  formatNullablePhase(breathPhaseText, sizeof(breathPhaseText), phaseFresh,
                      snapshot.breathPhase);
  formatNullablePhase(heartPhaseText, sizeof(heartPhaseText), phaseFresh,
                      snapshot.heartPhase);
  formatNullableFloat(breathRateRawText, sizeof(breathRateRawText),
                      snapshot.respirationValid, snapshot.respirationRate);
  formatNullableU32(phaseAgeText, sizeof(phaseAgeText), snapshot.phaseSamplePresent,
                    phaseAgeMs);
  formatNullableU32(phaseTimestampText, sizeof(phaseTimestampText),
                    snapshot.phaseSamplePresent, snapshot.phaseTimestampMs);
  formatNullableU32(phaseSequenceText, sizeof(phaseSequenceText),
                    snapshot.phaseSamplePresent, snapshot.phaseSequence);

  char json[1536];
  const int length = snprintf(
      json, sizeof(json),
      "{\"schema\":\"safenest.telemetry.v1\",\"device_id\":\"%s\","
      "\"boot_id\":\"%s\",\"seq\":%lu,\"uptime_ms\":%lu,"
      "\"firmware_version\":\"%s\","
      "\"resp_rate_bpm\":%s,\"heart_rate_bpm\":%s,\"co2_ppm\":%s,"
      "\"co2_sensor_model\":\"%s\","
      "\"co2_event_identity_class\":\"%s\","
      "\"co2_measurement_event_id\":%lu,"
      "\"co2_measurement_monotonic_ms\":%lu,"
      "\"co2_measurement_event_valid\":%s,\"co2_preheat\":%s,"
      "\"co2_preheat_complete\":%s,"
      "\"pir_motion\":%s,"
      "\"valid\":{\"respiration\":%s,\"heart\":%s,\"co2\":%s},"
      "\"mmwave\":{\"breath_phase\":%s,\"total_phase\":%s,"
      "\"heart_phase\":%s,\"breath_rate_raw\":%s,"
      "\"human_detected_raw\":%s,"
      "\"phase_age_ms\":%s,\"ts_monotonic_ms\":%s,\"seq\":%s,"
      "\"firmware_version\":\"%s\",\"schema_version\":\"%s\"}}",
      DEVICE_ID, bootId, static_cast<unsigned long>(snapshot.sequence),
      static_cast<unsigned long>(snapshot.uptimeMs), NODE_FIRMWARE_VERSION,
      respiration, heart, co2, CO2_SENSOR_MODEL, CO2_EVENT_IDENTITY_CLASS,
      static_cast<unsigned long>(snapshot.co2MeasurementEventId),
      static_cast<unsigned long>(snapshot.co2MeasurementMonotonicMs),
      snapshot.co2MeasurementEventValid ? "true" : "false",
      snapshot.co2Preheat ? "true" : "false",
      // === 온디바이스 CO2 AI(C-B6 / H150)를 살리는 한 줄 ===
      // Pi 의 h150_model_input_eligible() 은 `preheat_complete is True` 일 때만
      // CO2 를 모델 입력으로 받습니다. 그런데 Pi 의
      // _optional_co2_preheat_complete() 는 canonical 필드가 없으면 펌웨어의
      // `co2_preheat` 를 **부호 반전 없이** 그대로 preheat_complete 로 씁니다.
      // co2_preheat 는 "지금 예열 중인가"(예열 중 true)라서 의미가 정반대입니다.
      //   예열 중  : co2_preheat=true  -> preheat_complete=true  (틀림)
      //   예열 끝  : co2_preheat=false -> preheat_complete=false (틀림)
      // 결과적으로 예열이 끝난 뒤에도 CO2 는 영원히 모델 입력에서 제외됩니다.
      // canonical 필드를 우리가 직접 보내면 Pi 가 이쪽을 우선하므로,
      // 라즈베리파이 코드를 한 줄도 안 고치고 CO2 AI 가 살아납니다.
      snapshot.co2Preheat ? "false" : "true",
      snapshot.pirMotion ? "true" : "false",
      snapshot.respirationValid ? "true" : "false",
      snapshot.heartValid ? "true" : "false",
      snapshot.co2Valid ? "true" : "false", breathPhaseText, totalPhaseText,
      heartPhaseText, breathRateRawText, humanDetectedText, phaseAgeText,
      phaseTimestampText, phaseSequenceText, NODE_FIRMWARE_VERSION,
      MMWAVE_SCHEMA_VERSION);
  if (length <= 0 || static_cast<size_t>(length) >= sizeof(json)) return false;

  payloadLength = static_cast<size_t>(length);
  memcpy(lastTelemetryJson, json, payloadLength);
  lastTelemetryJson[payloadLength] = '\0';
  lastTelemetryJsonLength = payloadLength;

  uint8_t packet[PACKET_HEADER_SIZE + sizeof(json)];
  makePacketHeader(packet, PACKET_TELEMETRY_JSON, snapshot.sequence,
                   static_cast<uint32_t>(length));
  memcpy(packet + PACKET_HEADER_SIZE, json, payloadLength);
  return writeAll(client, packet, PACKET_HEADER_SIZE + payloadLength, report);
}

// =============================================================================
// Thermal UDP 전송
// =============================================================================
uint8_t thermalPayloadByte(const ThermalTxFrame &frame, const uint8_t *meta,
                           size_t offset) {
  if (offset < THERMAL_META_SIZE) return meta[offset];
  const size_t pixelByte = offset - THERMAL_META_SIZE;
  const uint16_t pixel = frame.pixels[pixelByte / 2];
  return (pixelByte & 1) ? static_cast<uint8_t>(pixel)
                         : static_cast<uint8_t>(pixel >> 8);
}

uint32_t thermalFrameCrc32(const ThermalTxFrame &frame, const uint8_t *meta) {
  uint32_t crc = 0xFFFFFFFF;
  for (size_t offset = 0; offset < THERMAL_PAYLOAD_SIZE; ++offset) {
    crc ^= thermalPayloadByte(frame, meta, offset);
    for (uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc >> 1) ^ (0xEDB88320U & (0U - (crc & 1U)));
    }
  }
  return ~crc;
}

void logSlowDatagram(uint32_t frameSequence, uint16_t chunkIndex,
                     uint32_t durationMs) {
  static uint32_t lastLogMs = 0;
  const uint32_t now = millis();
  if (lastLogMs != 0 && static_cast<uint32_t>(now - lastLogMs) < 1000) return;
  lastLogMs = now;
  Serial.printf(
      "[udp-slow] frame=%lu chunk=%u sendto_ms=%lu errno=%ld -- 이 시간 동안 "
      "TCP 태스크는 송신할 수 없습니다\n",
      static_cast<unsigned long>(frameSequence), static_cast<unsigned>(chunkIndex),
      static_cast<unsigned long>(durationMs), static_cast<long>(udpLastErrno));
}

bool yieldRadioToTcp(uint32_t maxWaitMs) {
  const uint32_t startedMs = millis();
  bool waited = false;
  for (;;) {
    if (!tcpLinkHealthy) return false;
    if ((xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) == 0) {
      if (waited) thermalTcpYields = thermalTcpYields + 1;
      return true;
    }
    if (static_cast<uint32_t>(millis() - startedMs) >= maxWaitMs) return false;
    waited = true;
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

bool reclaimUdpHeap(WiFiUDP &udp, bool &udpStarted) {
  if ((xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) != 0) {
    heapReclaimSkippedTcp = heapReclaimSkippedTcp + 1;
    return false;
  }
  const uint32_t heapBefore = ESP.getFreeHeap();
  if (udpStarted) {
    udp.stop();
    udpStarted = false;
  }
  udpStarted = udp.begin(0);
  heapReclaims = heapReclaims + 1;
  Serial.printf(
      "[heap] reclaim=%lu skipped_tcp=%lu heap_before=%lu heap_after=%lu "
      "max_alloc=%lu udp_up=%d\n",
      static_cast<unsigned long>(heapReclaims),
      static_cast<unsigned long>(heapReclaimSkippedTcp),
      static_cast<unsigned long>(heapBefore),
      static_cast<unsigned long>(ESP.getFreeHeap()),
      static_cast<unsigned long>(ESP.getMaxAllocHeap()), udpStarted ? 1 : 0);
  return udpStarted;
}

ThermalSendResult sendThermalUdp(WiFiUDP &udp, const ThermalTxFrame &frame) {
  constexpr TickType_t MUTEX_TIMEOUT = pdMS_TO_TICKS(1000);
  if (!thermalUdpEnabled) return ThermalSendResult::Suppressed;
  // 백프레셔. TCP telemetry 가 Pi 와의 계약이고 thermal 은 best-effort 입니다.
  // 세션이 죽어 있는 동안 UDP 를 계속 밀면 바로 그것이 SYN 을 막습니다.
  if (!tcpLinkHealthy) return ThermalSendResult::Deferred;
  if (udpHoldoffActive(millis())) return ThermalSendResult::Deferred;

  uint8_t meta[THERMAL_META_SIZE];
  putU16(meta + 0, static_cast<uint16_t>(THERMAL_WIDTH));
  putU16(meta + 2, static_cast<uint16_t>(THERMAL_HEIGHT));
  putU32(meta + 4, frame.frameSequence);
  putU32(meta + 8, frame.uptimeMs);
  putU16(meta + 12, frame.minimumRaw);
  putU16(meta + 14, frame.maximumRaw);
  const uint32_t crc32 = thermalFrameCrc32(frame, meta);

  for (uint16_t chunkIndex = 0; chunkIndex < THERMAL_UDP_CHUNK_COUNT;) {
    if (!yieldRadioToTcp(UDP_YIELD_TO_TCP_MAX_MS)) {
      return tcpLinkHealthy ? ThermalSendResult::Preempted
                            : ThermalSendResult::Deferred;
    }
    if (udpHoldoffActive(millis())) {
      return chunkIndex == 0 ? ThermalSendResult::Deferred
                             : ThermalSendResult::Preempted;
    }

    const size_t offset = chunkIndex * THERMAL_UDP_CHUNK_SIZE;
    const uint16_t length = static_cast<uint16_t>(
        min(THERMAL_UDP_CHUNK_SIZE, THERMAL_PAYLOAD_SIZE - offset));
    uint8_t *header = thermalUdpDatagram;
    memcpy(header, THERMAL_UDP_MAGIC, 4);
    header[4] = THERMAL_UDP_VERSION;
    header[5] = PACKET_THERMAL_U16_BE;
    putU16(header + 6, static_cast<uint16_t>(THERMAL_UDP_HEADER_SIZE));
    putU32(header + 8, frame.frameSequence);
    putU16(header + 12, chunkIndex);
    putU16(header + 14, THERMAL_UDP_CHUNK_COUNT);
    putU32(header + 16, static_cast<uint32_t>(THERMAL_PAYLOAD_SIZE));
    putU32(header + 20, static_cast<uint32_t>(offset));
    putU16(header + 24, length);
    putU16(header + 26, 0);
    putU32(header + 28, crc32);
    for (uint16_t index = 0; index < length; ++index) {
      thermalUdpDatagram[THERMAL_UDP_HEADER_SIZE + index] =
          thermalPayloadByte(frame, meta, offset + index);
    }

    if (xSemaphoreTake(networkTxMutex, MUTEX_TIMEOUT) != pdTRUE) {
      return ThermalSendResult::Preempted;
    }
    // TCP 가 비트를 세우고 이 뮤텍스에서 대기 중이면 새치기하지 않고 돌려줍니다.
    if ((xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) != 0) {
      xSemaphoreGive(networkTxMutex);
      continue;
    }

    errno = 0;
    const uint32_t datagramStartedMs = millis();
    const bool sent =
        udp.beginPacket(rpiHostIp, THERMAL_UDP_PORT) &&
        udp.write(thermalUdpDatagram, THERMAL_UDP_HEADER_SIZE + length) ==
            THERMAL_UDP_HEADER_SIZE + length &&
        udp.endPacket() == 1;
    const uint32_t datagramMs = static_cast<uint32_t>(millis() - datagramStartedMs);
    if (!sent) udpLastErrno = errno;
    if (datagramMs > udpDatagramMaxMs) udpDatagramMaxMs = datagramMs;
    if (sent) {
      udpDatagramsSent = udpDatagramsSent + 1;
      udpBytesSent = udpBytesSent + THERMAL_UDP_HEADER_SIZE + length;
    }
    if (datagramMs >= UDP_DATAGRAM_WARN_MS) {
      udpSlowDatagrams = udpSlowDatagrams + 1;
      logSlowDatagram(frame.frameSequence, chunkIndex, datagramMs);
    }
    xSemaphoreGive(networkTxMutex);
    if (!sent) return ThermalSendResult::Failed;

    chunkIndex = static_cast<uint16_t>(chunkIndex + 1);
    if (chunkIndex < THERMAL_UDP_CHUNK_COUNT) {
      vTaskDelay(pdMS_TO_TICKS(UDP_CHUNK_GAP_MS));
    }
  }
  return ThermalSendResult::Sent;
}

// =============================================================================
// 네트워크 태스크
// =============================================================================
void logTcpDrop(const char *reason, uint32_t sessionStartedMs,
                uint32_t sessionPackets, int pendingRxBytes) {
  const uint32_t now = millis();
  const uint32_t sessionMs =
      sessionStartedMs == 0 ? 0 : static_cast<uint32_t>(now - sessionStartedMs);
  tcpDrops = tcpDrops + 1;
  if (sessionMs < 10000) tcpShortSessions = tcpShortSessions + 1;
  Serial.printf(
      "[tcp-drop] reason=%s session_ms=%lu session_packets=%lu "
      "since_last_send_ms=%ld gap_max_ms=%lu gap_late=%lu write_max_ms=%lu "
      "write_stalls=%lu partial_writes=%lu mutex_max_ms=%lu mutex_to=%lu "
      "tcp_errno=%ld rx_pending=%d udp_on=%d udp_dg=%lu udp_slow=%lu "
      "udp_dg_max_ms=%lu udp_frame_max_ms=%lu udp_errno=%ld rssi=%d "
      "heap=%lu min_heap=%lu max_alloc=%lu drops=%lu short_sessions=%lu "
      "write_to=%lu holdoff=%lu\n",
      reason, static_cast<unsigned long>(sessionMs),
      static_cast<unsigned long>(sessionPackets),
      lastTelemetrySentMs == 0 ? -1L : static_cast<long>(now - lastTelemetrySentMs),
      static_cast<unsigned long>(telemetryGapMaxMs),
      static_cast<unsigned long>(telemetryGapOverDeadline),
      static_cast<unsigned long>(tcpWriteMaxMs),
      static_cast<unsigned long>(tcpWriteStalls),
      static_cast<unsigned long>(tcpPartialWrites),
      static_cast<unsigned long>(tcpMutexWaitMaxMs),
      static_cast<unsigned long>(tcpMutexTimeouts),
      static_cast<long>(tcpLastErrno), pendingRxBytes, thermalUdpEnabled ? 1 : 0,
      static_cast<unsigned long>(udpDatagramsSent),
      static_cast<unsigned long>(udpSlowDatagrams),
      static_cast<unsigned long>(udpDatagramMaxMs),
      static_cast<unsigned long>(udpFrameMaxMs), static_cast<long>(udpLastErrno),
      static_cast<int>(WiFi.RSSI()), static_cast<unsigned long>(ESP.getFreeHeap()),
      static_cast<unsigned long>(ESP.getMinFreeHeap()),
      static_cast<unsigned long>(ESP.getMaxAllocHeap()),
      static_cast<unsigned long>(tcpDrops),
      static_cast<unsigned long>(tcpShortSessions),
      static_cast<unsigned long>(tcpWriteTimeouts),
      static_cast<unsigned long>(udpHoldoffEvents));
}

void telemetryTcpTask(void *parameter) {
  (void)parameter;
  WiFiClient client;
  TelemetrySnapshot telemetry{};
  uint32_t lastDequeuedSequence = 0;
  uint32_t lastConnectDurationMs = 0;
  uint32_t lastQueueWaitMs = 0;
  uint32_t sessionStartedMs = 0;
  uint32_t sessionPackets = 0;
  uint32_t consecutiveWriteTimeouts = 0;
  uint32_t consecutiveConnectFailures = 0;
  bool sessionOpen = false;

  for (;;) {
    uint32_t mutexWaitMs = 0;

    if (WiFi.status() != WL_CONNECTED) {
      tcpLinkHealthy = false;
      rpiHostIpValid = false;
      wifiMulti.run(5000);  // 등록된 후보 중 잡히는 쪽으로
      if (sessionOpen) {
        logTcpDrop("wifi_down", sessionStartedMs, sessionPackets, client.available());
        sessionOpen = false;
      }
      if (client.connected() && beginTcpCritical(mutexWaitMs)) {
        client.stop();
        endTcpCritical();
      }
      vTaskDelay(pdMS_TO_TICKS(250));
      continue;
    }

    if (!client.connected()) {
      // 재접속 전체 구간 동안 thermal 송신기를 세웁니다. 핸드셰이크가 끝나려면
      // 무선이 조용해야 하고, TCP_CRITICAL_BIT 는 뮤텍스를 쥔 순간만 덮습니다.
      tcpLinkHealthy = false;
      if (sessionOpen) {
        tcpPeerClosed = tcpPeerClosed + 1;
        logTcpDrop("peer_closed", sessionStartedMs, sessionPackets, client.available());
        sessionOpen = false;
      }
      if (!ensureRpiHostIp()) {
        Serial.printf(
            "[network] %s 주소를 아직 못 찾았습니다 (mDNS 응답 없음). 재시도합니다.\n",
            RPI_HOST);
        vTaskDelay(pdMS_TO_TICKS(1000));
        continue;
      }
      Serial.printf("[network] connecting to %s (%s):%u\n", RPI_HOST,
                    rpiHostIp.toString().c_str(), RPI_PORT);
      bool connected = false;
      if (beginTcpCritical(mutexWaitMs)) {
        const uint32_t connectStartedMs = millis();
        errno = 0;
        connected = client.connect(rpiHostIp, RPI_PORT, TCP_CONNECT_TIMEOUT_MS);
        lastConnectDurationMs = millis() - connectStartedMs;
        if (!connected) {
          tcpLastErrno = errno;
          client.stop();
          rpiHostIpValid = false;  // 주소가 바뀌었을 수 있으니 다시 찾습니다
        }
        endTcpCritical();
      } else {
        tcpMutexTimeouts = tcpMutexTimeouts + 1;
      }
      if (!connected) {
        tcpConnectionFailures = tcpConnectionFailures + 1;
        ++consecutiveConnectFailures;
        Serial.printf(
            "[tcp-connect-fail] host=%s:%u mutex_wait_ms=%lu connect_ms=%lu "
            "errno=%ld failures=%lu my_ip=%s rssi=%d -- Pi 에서 "
            "`ss -ltn | grep :%u` 로 수신 포트를 확인하세요\n",
            RPI_HOST, static_cast<unsigned>(RPI_PORT),
            static_cast<unsigned long>(mutexWaitMs),
            static_cast<unsigned long>(lastConnectDurationMs),
            static_cast<long>(tcpLastErrno),
            static_cast<unsigned long>(tcpConnectionFailures),
            WiFi.localIP().toString().c_str(), static_cast<int>(WiFi.RSSI()),
            static_cast<unsigned>(RPI_PORT));
        // 연결이 계속 안 되면 소켓이 아니라 Wi-Fi 결합 자체를 의심합니다.
        // AP 가 우리를 내보냈는데 STA 가 모르는 상태면 재결합만이 유일한 탈출구입니다.
        if (consecutiveConnectFailures >= WIFI_REASSOCIATE_AFTER_CONNECT_FAILURES) {
          consecutiveConnectFailures = 0;
          wifiReassociations = wifiReassociations + 1;
          rpiHostIpValid = false;
          Serial.printf(
              "[wifi-reassoc] TCP connect 가 %lu회 연속 실패했습니다. "
              "WiFi.status()=CONNECTED rssi=%d 인데도 프레임이 안 지나가는 "
              "상태로 보고 Wi-Fi 를 다시 결합합니다. reassoc=%lu\n",
              static_cast<unsigned long>(WIFI_REASSOCIATE_AFTER_CONNECT_FAILURES),
              static_cast<int>(WiFi.RSSI()),
              static_cast<unsigned long>(wifiReassociations));
          WiFi.disconnect(false, false);
          vTaskDelay(pdMS_TO_TICKS(300));
          wifiMulti.run(8000);
          vTaskDelay(pdMS_TO_TICKS(500));
        } else {
          vTaskDelay(pdMS_TO_TICKS(1000));
        }
        continue;
      }
      consecutiveConnectFailures = 0;
      client.setNoDelay(true);
      sessionStartedMs = millis();
      sessionPackets = 0;
      sessionOpen = true;
      tcpSessions = tcpSessions + 1;
      // 첫 telemetry 쓰기가 성공하기 전에는 tcpLinkHealthy 를 켜지 않습니다.
      // SYN-ACK 와 첫 JSON 사이에 thermal 이 TX 큐를 다시 채우면 안 됩니다.
      Serial.printf(
          "[network] Raspberry Pi connected: %s:%u session=%lu connect_ms=%lu\n",
          RPI_HOST, static_cast<unsigned>(RPI_PORT),
          static_cast<unsigned long>(tcpSessions),
          static_cast<unsigned long>(lastConnectDurationMs));
    }

    if (xQueueReceive(telemetryQueue, &telemetry, 0) == pdTRUE) {
      telemetryQueueOverwrites =
          telemetryQueueOverwrites + telemetry.sequence - lastDequeuedSequence - 1;
      lastDequeuedSequence = telemetry.sequence;
      lastQueueWaitMs = static_cast<uint32_t>(millis() - telemetry.uptimeMs);

      size_t jsonPayloadLength = 0;
      bool sent = false;
      bool socketClosedByFailure = false;
      bool writeAttempted = false;
      uint32_t writeDurationMs = 0;
      TcpWriteReport report{};

      if (beginTcpCritical(mutexWaitMs)) {
        writeAttempted = true;
        const uint32_t writeStartedMs = millis();
        sent = sendTelemetry(client, telemetry, jsonPayloadLength, report);
        writeDurationMs = millis() - writeStartedMs;
        if (!sent) {
          tcpLastErrno = report.lastErrno;
          // 0바이트 fail-fast 타임아웃은 Pi 에 도달하지 않았으니 세션을 유지합니다.
          // 반쪽 SNST 헤더/바디는 수신기를 desync 시키므로 그때만 닫습니다.
          if (report.bytesWritten > 0 || !report.connectedAtEnd) {
            client.stop();
            socketClosedByFailure = true;
          }
        }
        endTcpCritical();
        if (writeDurationMs > tcpWriteMaxMs) tcpWriteMaxMs = writeDurationMs;
        if (writeDurationMs >= TCP_WRITE_WARN_MS) {
          tcpSlowWrites = tcpSlowWrites + 1;
          requestUdpHoldoff(millis(), UDP_SLOW_TCP_HOLDOFF_MS);
        }
        if (report.zeroWrites > 0) tcpWriteStalls = tcpWriteStalls + 1;
        if (report.partialWrites > 0) tcpPartialWrites = tcpPartialWrites + 1;
      } else {
        tcpMutexTimeouts = tcpMutexTimeouts + 1;
        Serial.printf(
            "[tcp-blocked] seq=%lu mutex_wait_ms=%lu timeouts=%lu -- thermal UDP "
            "태스크가 TX 뮤텍스를 한도 이상 쥐고 있어 이 패킷은 소켓에 못 갔습니다\n",
            static_cast<unsigned long>(telemetry.sequence),
            static_cast<unsigned long>(mutexWaitMs),
            static_cast<unsigned long>(tcpMutexTimeouts));
      }

      if (!sent) {
        tcpSendFailures = tcpSendFailures + 1;
        requestUdpHoldoff(millis(), UDP_SLOW_TCP_HOLDOFF_MS);
        if (!socketClosedByFailure && writeAttempted) {
          tcpWriteTimeouts = tcpWriteTimeouts + 1;
          ++consecutiveWriteTimeouts;
          // 연속 실패가 임계값을 넘으면 소켓이 좀비입니다. 붙들고 있어봐야
          // 송신 버퍼만 계속 차 있고 heap 도 안 돌아옵니다. 끊고 다시 붙습니다.
          if (consecutiveWriteTimeouts >= TCP_MAX_CONSECUTIVE_WRITE_TIMEOUTS) {
            if (beginTcpCritical(mutexWaitMs)) {
              client.stop();
              endTcpCritical();
            } else {
              client.stop();
            }
            socketClosedByFailure = true;
            tcpLinkHealthy = false;
            tcpZombieRecoveries = tcpZombieRecoveries + 1;
            Serial.printf(
                "[tcp-zombie] %lu회 연속 0바이트 write 타임아웃 -> 소켓을 강제로 "
                "끊고 재접속합니다. Pi 가 이미 닫았는데 FIN/RST 이 무선 손실로 "
                "도착하지 못한 상태입니다. recoveries=%lu heap=%lu rssi=%d\n",
                static_cast<unsigned long>(consecutiveWriteTimeouts),
                static_cast<unsigned long>(tcpZombieRecoveries),
                static_cast<unsigned long>(ESP.getFreeHeap()),
                static_cast<int>(WiFi.RSSI()));
            consecutiveWriteTimeouts = 0;
            if (sessionOpen) {
              logTcpDrop("write_timeout_zombie", sessionStartedMs, sessionPackets, 0);
              sessionOpen = false;
            }
          }
          Serial.printf(
              "[tcp-send-timeout] seq=%lu wrote=%u/%u elapsed_ms=%lu stall_ms=%lu "
              "zero_writes=%u errno=%ld kept_open=%d timeouts=%lu\n",
              static_cast<unsigned long>(telemetry.sequence),
              static_cast<unsigned>(report.bytesWritten),
              static_cast<unsigned>(PACKET_HEADER_SIZE + jsonPayloadLength),
              static_cast<unsigned long>(report.elapsedMs),
              static_cast<unsigned long>(report.longestStallMs),
              static_cast<unsigned>(report.zeroWrites),
              static_cast<long>(report.lastErrno),
              socketClosedByFailure ? 0 : 1,
              static_cast<unsigned long>(tcpWriteTimeouts));
        }
      }

      if (socketClosedByFailure) {
        tcpLinkHealthy = false;
        Serial.printf(
            "[tcp-send-fail] seq=%lu wrote=%u/%u elapsed_ms=%lu stall_ms=%lu "
            "zero_writes=%u partial=%u errno=%ld connected=%d failures=%lu\n",
            static_cast<unsigned long>(telemetry.sequence),
            static_cast<unsigned>(report.bytesWritten),
            static_cast<unsigned>(PACKET_HEADER_SIZE + jsonPayloadLength),
            static_cast<unsigned long>(report.elapsedMs),
            static_cast<unsigned long>(report.longestStallMs),
            static_cast<unsigned>(report.zeroWrites),
            static_cast<unsigned>(report.partialWrites),
            static_cast<long>(report.lastErrno), report.connectedAtEnd ? 1 : 0,
            static_cast<unsigned long>(tcpSendFailures));
        if (sessionOpen) {
          logTcpDrop("write_failed", sessionStartedMs, sessionPackets, 0);
          sessionOpen = false;
        }
      }

      if (sent) {
        tcpLinkHealthy = true;
        consecutiveWriteTimeouts = 0;
        const uint32_t completedMs = millis();
        if (lastTelemetrySentMs != 0) {
          const uint32_t gapMs =
              static_cast<uint32_t>(completedMs - lastTelemetrySentMs);
          if (gapMs > telemetryGapMaxMs) telemetryGapMaxMs = gapMs;
          if (gapMs >= PI_PACKET_DEADLINE_MS) {
            telemetryGapOverDeadline = telemetryGapOverDeadline + 1;
          }
          if (gapMs >= TELEMETRY_GAP_WARN_MS) {
            telemetryGapOverWarn = telemetryGapOverWarn + 1;
            Serial.printf(
                "[tcp-gap] seq=%lu gap_ms=%lu pi_deadline_ms=%lu queue_wait_ms=%lu "
                "mutex_wait_ms=%lu write_ms=%lu stall_ms=%lu zero_writes=%u "
                "overwrites=%lu udp_on=%d udp_dg_max_ms=%lu rssi=%d%s\n",
                static_cast<unsigned long>(telemetry.sequence),
                static_cast<unsigned long>(gapMs),
                static_cast<unsigned long>(PI_PACKET_DEADLINE_MS),
                static_cast<unsigned long>(lastQueueWaitMs),
                static_cast<unsigned long>(mutexWaitMs),
                static_cast<unsigned long>(writeDurationMs),
                static_cast<unsigned long>(report.longestStallMs),
                static_cast<unsigned>(report.zeroWrites),
                static_cast<unsigned long>(telemetryQueueOverwrites),
                thermalUdpEnabled ? 1 : 0,
                static_cast<unsigned long>(udpDatagramMaxMs),
                static_cast<int>(WiFi.RSSI()),
                gapMs >= PI_PACKET_DEADLINE_MS ? "  <<< EXCEEDS_PI_DEADLINE" : "");
          }
        }
        lastTelemetrySentMs = completedMs;
        telemetryPacketsSent = telemetryPacketsSent + 1;
        ++sessionPackets;
      }

      if (!sent) continue;
    }

    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

void thermalUdpTask(void *parameter) {
  (void)parameter;
  WiFiUDP udp;
  bool udpStarted = false;
  uint32_t lastDequeuedSequence = 0;
  uint32_t consecutiveHardFailures = 0;
  uint32_t enomemBackoffMs = UDP_ENOMEM_BACKOFF_MIN_MS;

  for (;;) {
    if (WiFi.status() != WL_CONNECTED) {
      rpiHostIpValid = false;
      if (udpStarted) {
        udp.stop();
        udpStarted = false;
      }
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }
    if (!ensureRpiHostIp()) {
      vTaskDelay(pdMS_TO_TICKS(250));
      continue;
    }
    if (!udpStarted) {
      udpStarted = udp.begin(0);
      if (!udpStarted) {
        vTaskDelay(pdMS_TO_TICKS(250));
        continue;
      }
    }

    const uint32_t now = millis();
    if (ESP.getFreeHeap() < HEAP_RECLAIM_LOW_WATER_BYTES) {
      requestUdpHoldoff(now, enomemBackoffMs);
    }

    if (xQueueReceive(thermalQueue, &thermalNetworkFrame, 0) == pdTRUE) {
      thermalQueueOverwrites = thermalQueueOverwrites +
                               thermalNetworkFrame.frameSequence -
                               lastDequeuedSequence - 1;
      lastDequeuedSequence = thermalNetworkFrame.frameSequence;
      const uint32_t frameStartedMs = millis();
      const ThermalSendResult result = sendThermalUdp(udp, thermalNetworkFrame);
      const uint32_t frameMs = static_cast<uint32_t>(millis() - frameStartedMs);
      if (frameMs > udpFrameMaxMs) udpFrameMaxMs = frameMs;

      switch (result) {
        case ThermalSendResult::Sent:
          thermalUdpFramesSent = thermalUdpFramesSent + 1;
          consecutiveHardFailures = 0;
          enomemBackoffMs = UDP_ENOMEM_BACKOFF_MIN_MS;
          udpBackoffMs = 0;
          break;
        case ThermalSendResult::Preempted:
          thermalFramesPreempted = thermalFramesPreempted + 1;
          break;
        case ThermalSendResult::Failed: {
          thermalUdpSendFailures = thermalUdpSendFailures + 1;
          const int err = static_cast<int>(udpLastErrno);
          if (thermalUdpSendFailures <= 3 || thermalUdpSendFailures % 25 == 0) {
            Serial.printf(
                "[udp-fail] frame=%lu frame_ms=%lu errno=%ld failures=%lu "
                "consecutive=%lu\n",
                static_cast<unsigned long>(thermalNetworkFrame.frameSequence),
                static_cast<unsigned long>(frameMs), static_cast<long>(udpLastErrno),
                static_cast<unsigned long>(thermalUdpSendFailures),
                static_cast<unsigned long>(consecutiveHardFailures + 1));
          }
          if (err == ENOMEM || err == ENOBUFS || isTransientSendErrno(err)) {
            // lwIP TX pbuf 고갈. 소켓을 새로 만들어도 드라이버 큐의 버퍼는
            // 안 돌아오고 1460바이트 TX 버퍼 malloc 이 heap 만 조각냅니다.
            consecutiveHardFailures = 0;
            requestUdpHoldoff(millis(), enomemBackoffMs);
            udpBackoffMs = enomemBackoffMs;
            static uint32_t lastBackoffLogMs = 0;
            const uint32_t backoffNow = millis();
            if (lastBackoffLogMs == 0 ||
                static_cast<uint32_t>(backoffNow - lastBackoffLogMs) >= 1000) {
              lastBackoffLogMs = backoffNow;
              Serial.printf(
                  "[udp-backoff] errno=%ld backoff_ms=%lu heap=%lu max_alloc=%lu "
                  "holdoff=%lu\n",
                  static_cast<long>(err),
                  static_cast<unsigned long>(enomemBackoffMs),
                  static_cast<unsigned long>(ESP.getFreeHeap()),
                  static_cast<unsigned long>(ESP.getMaxAllocHeap()),
                  static_cast<unsigned long>(udpHoldoffEvents));
            }
            if (enomemBackoffMs < UDP_ENOMEM_BACKOFF_MAX_MS) {
              enomemBackoffMs = enomemBackoffMs * 2;
              if (enomemBackoffMs > UDP_ENOMEM_BACKOFF_MAX_MS) {
                enomemBackoffMs = UDP_ENOMEM_BACKOFF_MAX_MS;
              }
            }
          } else {
            ++consecutiveHardFailures;
            if (udpErrorLooksLikeDeadSocket(err) ||
                consecutiveHardFailures >= UDP_MAX_CONSECUTIVE_FAILURES) {
              if (reclaimUdpHeap(udp, udpStarted)) {
                consecutiveHardFailures = 0;
                udpSocketRestarts = udpSocketRestarts + 1;
                Serial.printf(
                    "[udp-restart] socket rebuilt after hard failure errno=%ld "
                    "restarts=%lu\n",
                    static_cast<long>(udpLastErrno),
                    static_cast<unsigned long>(udpSocketRestarts));
              }
            }
          }
          break;
        }
        case ThermalSendResult::Suppressed:
          thermalFramesSuppressed = thermalFramesSuppressed + 1;
          break;
        case ThermalSendResult::Deferred:
          thermalFramesDeferred = thermalFramesDeferred + 1;
          break;
      }
    }
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

// =============================================================================
// 로그
// =============================================================================
// 시리얼에 찍고, 같은 줄을 Wi-Fi 브로드캐스트로도 보냅니다.
// 외부 전원으로 돌려 USB 가 없을 때 이게 유일한 관측 경로가 됩니다.
void diagPrintf(const char *format, ...) {
  char line[640];
  va_list args;
  va_start(args, format);
  const int length = vsnprintf(line, sizeof(line), format, args);
  va_end(args);
  if (length <= 0) return;
  const size_t used = static_cast<size_t>(length) >= sizeof(line)
                          ? sizeof(line) - 1
                          : static_cast<size_t>(length);
  Serial.print(line);

  if (!diagUdpEnabled) return;
  if (WiFi.status() != WL_CONNECTED) return;
  // TCP telemetry 가 소켓을 쥐고 있는 동안에는 무선을 건드리지 않습니다.
  // 진단 로그가 본 계약을 늦추는 일은 없어야 합니다.
  if ((xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) != 0) {
    diagUdpLinesDropped = diagUdpLinesDropped + 1;
    return;
  }
  if (!diagUdpStarted) {
    diagUdpStarted = diagUdp.begin(0);
    if (!diagUdpStarted) return;
  }
  const bool sent = diagUdp.beginPacket(WiFi.broadcastIP(), DIAG_LOG_UDP_PORT) &&
                    diagUdp.write(reinterpret_cast<const uint8_t *>(line), used) ==
                        used &&
                    diagUdp.endPacket() == 1;
  if (sent) {
    diagUdpLinesSent = diagUdpLinesSent + 1;
  } else {
    diagUdpLinesDropped = diagUdpLinesDropped + 1;
  }
}

// 실제로 나간 JSON 과, 각 null 의 사유. 이게 없어서 "값이 안 온다"를
// 센서 문제인지 링크 문제인지 구분할 수 없었습니다.
void logTransmittedTelemetry(uint32_t now) {
  if (!txLogEnabled) return;
  if (!scheduleDue(now, lastTxLogMs, TX_LOG_PERIOD_MS)) return;
  if (lastTelemetryJsonLength == 0) {
    diagPrintf(
        "[tx] 아직 전송된 telemetry 가 없습니다. wifi=%s tcp=%s seq=%lu "
        "conn_fail=%lu send_fail=%lu\n",
        WiFi.status() == WL_CONNECTED ? "up" : "down",
        tcpLinkHealthy ? "up" : "down",
        static_cast<unsigned long>(telemetrySequence),
        static_cast<unsigned long>(tcpConnectionFailures),
        static_cast<unsigned long>(tcpSendFailures));
    return;
  }
  diagPrintf("[tx] %s\n", lastTelemetryJson);

  const bool respFresh = isFresh(lastRespirationMs, now, MMWAVE_STALE_MS);
  const bool heartFresh = isFresh(lastHeartMs, now, MMWAVE_STALE_MS);
  const bool co2Fresh = isFresh(lastCo2Ms, now, CO2_STALE_MS);
  const bool phaseFresh =
      phaseSamplePresent &&
      static_cast<uint32_t>(now - lastPhaseMs) < PHASE_MAX_AGE_MS;
  diagPrintf(
      "[why] resp=%s heart=%s co2=%s phase=%s presence=%s | "
      "mmw_frames=%lu co2_accepted=%lu thermal_frames=%lu udp_sent=%lu\n",
      nullReasonText(floatReason(respFresh, lastRespirationMs, respirationRate)),
      nullReasonText(floatReason(heartFresh, lastHeartMs, heartRate)),
      lastCo2Ms == 0 ? "never_seen" : (co2Fresh ? "ok" : "stale"),
      phaseSamplePresent ? (phaseFresh ? "ok" : "stale") : "never_seen",
      lastPresenceMs == 0
          ? "never_seen"
          : (isFresh(lastPresenceMs, now, PRESENCE_MAX_AGE_MS) ? "ok" : "stale"),
      static_cast<unsigned long>(mmWave.framesParsed()),
      static_cast<unsigned long>(co2AcceptedSamples),
      static_cast<unsigned long>(thermalSequence),
      static_cast<unsigned long>(thermalUdpFramesSent));
}

// -----------------------------------------------------------------------------
// 온디바이스 AI 입력 준비 상태
//
// Pi 쪽 세 모델은 각각 "이 노드가 무엇을 얼마나 보내주느냐"에 걸려 있습니다.
// 그 조건을 노드 쪽에서 그대로 계산해 보여줍니다. 대시보드가
// WINDOW_NOT_READY / INPUT_UNAVAILABLE 을 띄울 때 원인이 센서인지 시간인지
// 바로 구분됩니다.
//
//  mmWave B23  : breath_phase 를 300 sample @ 10 Hz(=30 s) 창으로 씁니다.
//                창은 *새로운* mmwave.seq 에서만 전진합니다(같은 seq 재전송은
//                Pi 가 건너뜁니다). 즉 채워지는 속도는 TCP 10 Hz 가 아니라
//                MR60 이 0x0A13 phase 리포트를 내는 실제 속도입니다.
//                Pi 의 phase_age 허용치는 1000 ms, 이 노드는 500 ms 로 더 엄격.
//  CO2 C-B6    : co2_measurement_event_id 기준 150 s 이상의 이력이 필요합니다.
//                5 s 샘플 주기면 최소 31개 이벤트. 그리고 preheat_complete 가
//                true 여야만 모델 입력에 들어갑니다(3분 예열).
//  Thermal     : 프레임 한 장이면 즉시 추론합니다. udp_sent 가 0 이 아니면 됩니다.
// -----------------------------------------------------------------------------
constexpr uint32_t B23_WINDOW_SAMPLES = 300;
constexpr uint32_t B23_TARGET_RATE_HZ = 10;
constexpr uint32_t H150_WINDOW_MS = 150000;

void logAiReadiness(uint32_t now) {
  static uint32_t lastPhaseSeqSample = 0;
  static uint32_t lastCo2EventSample = 0;
  static uint32_t lastSampleMs = 0;

  const uint32_t windowMs =
      lastSampleMs == 0 ? HEALTH_LOG_PERIOD_MS
                        : static_cast<uint32_t>(now - lastSampleMs);
  const uint32_t divisor = windowMs == 0 ? 1 : windowMs;
  const uint32_t phaseHz100 =
      (phaseSequence - lastPhaseSeqSample) * 100000UL / divisor;  // Hz × 100

  // 남은 phase 이벤트 수를 현재 속도로 나눈 예상 시간. 속도가 0 이면 -1.
  long secondsToWindow = -1;
  if (phaseHz100 > 0) {
    const uint32_t remaining =
        phaseSequence >= B23_WINDOW_SAMPLES ? 0 : B23_WINDOW_SAMPLES - phaseSequence;
    secondsToWindow = static_cast<long>(remaining * 100UL / phaseHz100);
  }

  const bool preheatDone = co2ModelPreheatDone(now);
  const bool co2EventOk = co2MeasurementEventValid && isFresh(lastCo2Ms, now, CO2_STALE_MS);
  const uint32_t co2HistoryNeeded = H150_WINDOW_MS / CO2_UART_SAMPLE_PERIOD_MS + 1;

  diagPrintf(
      "[ai]     mmwave_b23: phase_events=%lu/%lu rate=%lu.%02lu Hz eta=%lds "
      "(창은 새 mmwave.seq 에서만 전진) | co2_c_b6: events=%lu/%lu preheat_done=%d "
      "event_valid=%d eligible=%s | thermal: frames_sent=%lu ready=%s\n",
      static_cast<unsigned long>(phaseSequence),
      static_cast<unsigned long>(B23_WINDOW_SAMPLES),
      static_cast<unsigned long>(phaseHz100 / 100),
      static_cast<unsigned long>(phaseHz100 % 100), secondsToWindow,
      static_cast<unsigned long>(co2MeasurementEventId),
      static_cast<unsigned long>(co2HistoryNeeded), preheatDone ? 1 : 0,
      co2EventOk ? 1 : 0,
      (preheatDone && co2EventOk) ? "YES" : "NO",
      static_cast<unsigned long>(thermalUdpFramesSent),
      thermalUdpFramesSent > 0 ? "YES" : "NO");

  if (phaseSequence == 0) {
    Serial.println(
        "[ai]     WARNING: phase 이벤트가 0 입니다. MR60 이 0x0A13 "
        "HeartBreathPhase 리포트를 안 내고 있습니다 -> mmWave AI 는 영원히 "
        "WINDOW_NOT_READY 입니다. 센서 앞 1~2 m 에 사람이 정면으로 있어야 하고, "
        "UART2(16/17) 배선과 5V 전원을 확인하세요.");
  }
  if (preheatDone && co2MeasurementEventId == 0) {
    Serial.println(
        "[ai]     WARNING: 예열은 끝났는데 CO2 measurement event 가 0 입니다 "
        "-> CO2 AI 입력 없음. 위 [health] co2 줄의 timeout/csum_fail/hdr_fail 을 "
        "보세요.");
  }
  (void)lastCo2EventSample;

  lastPhaseSeqSample = phaseSequence;
  lastCo2EventSample = co2MeasurementEventId;
  lastSampleMs = now;
}

void logHealth(uint32_t now) {
  if (!scheduleDue(now, lastHealthLogMs, HEALTH_LOG_PERIOD_MS)) return;

  const bool wifiUp = WiFi.status() == WL_CONNECTED;
  const IPAddress ip = WiFi.localIP();

  diagPrintf("[health] ===== up=%lus =====\n",
                static_cast<unsigned long>(now / 1000));
  // localIP() 가 있어야 "Pi 가 죽었다"와 "내가 다른 서브넷이다"를 구분합니다.
  diagPrintf(
      "[health] link    wifi=%s(%s) ip=%u.%u.%u.%u rssi=%d rpi=%s:%u tcp=%s "
      "sessions=%lu drops=%lu sent=%lu\n",
      wifiUp ? "up" : "down", WiFi.SSID().c_str(), static_cast<unsigned>(ip[0]),
      static_cast<unsigned>(ip[1]), static_cast<unsigned>(ip[2]),
      static_cast<unsigned>(ip[3]), wifiUp ? static_cast<int>(WiFi.RSSI()) : 0,
      RPI_HOST, static_cast<unsigned>(RPI_PORT), tcpLinkHealthy ? "up" : "down",
      static_cast<unsigned long>(tcpSessions),
      static_cast<unsigned long>(tcpDrops),
      static_cast<unsigned long>(telemetryPacketsSent));

  diagPrintf(
      "[health] tcp     conn_fail=%lu send_fail=%lu write_to=%lu queue_ovw=%lu "
      "gap_max_ms=%lu gap_late=%lu zombie_recover=%lu wifi_reassoc=%lu\n",
      static_cast<unsigned long>(tcpConnectionFailures),
      static_cast<unsigned long>(tcpSendFailures),
      static_cast<unsigned long>(tcpWriteTimeouts),
      static_cast<unsigned long>(telemetryQueueOverwrites),
      static_cast<unsigned long>(telemetryGapMaxMs),
      static_cast<unsigned long>(telemetryGapOverDeadline),
      static_cast<unsigned long>(tcpZombieRecoveries),
      static_cast<unsigned long>(wifiReassociations));

  diagPrintf(
      "[health] thermal mode=%s started=%d frames=%lu udp_sent=%lu udp_fail=%lu "
      "preempt=%lu defer=%lu holdoff=%lu restarts=%lu hdr_mismatch=%lu "
      "hdr_layout=%s flat=%lu strict_drop=%lu status_fail=%lu queue_ovw=%lu "
      "ready_demote=%lu\n",
      thermalReadyModeText(thermalReadyMode), thermalStarted ? 1 : 0,
      static_cast<unsigned long>(thermalSequence),
      static_cast<unsigned long>(thermalUdpFramesSent),
      static_cast<unsigned long>(thermalUdpSendFailures),
      static_cast<unsigned long>(thermalFramesPreempted),
      static_cast<unsigned long>(thermalFramesDeferred),
      static_cast<unsigned long>(udpHoldoffEvents),
      static_cast<unsigned long>(udpSocketRestarts),
      static_cast<unsigned long>(thermalHeaderMismatches),
      thermalHeaderLayoutResolved ? "resolved"
                                  : (thermalHeaderLayoutGiveUp ? "unresolved"
                                                               : "probing"),
      static_cast<unsigned long>(thermalFlatFrames),
      static_cast<unsigned long>(thermalStrictDrops),
      static_cast<unsigned long>(thermalStatusQueryFailures),
      static_cast<unsigned long>(thermalQueueOverwrites),
      static_cast<unsigned long>(thermalReadyDemotions));

  char respText[16], heartText[16];
  formatNullableFloat(respText, sizeof(respText),
                      isFresh(lastRespirationMs, now, MMWAVE_STALE_MS),
                      respirationRate);
  formatNullableFloat(heartText, sizeof(heartText),
                      isFresh(lastHeartMs, now, MMWAVE_STALE_MS), heartRate);
  diagPrintf(
      "[health] sensors resp=%s heart=%s co2=%u pir=%d co2_age_ms=%ld "
      "resp_age_ms=%ld heart_age_ms=%ld presence_age_ms=%ld phase=%.4f "
      "phase_age_ms=%ld phase_seq=%lu mmw_ok=%lu mmw_frames=%lu "
      "mmw_age_ms=%ld mmw_uart=%u mmw_miss=%lu\n",
      respText, heartText, static_cast<unsigned>(co2Ppm), pirMotion ? 1 : 0,
      lastCo2Ms == 0 ? -1L : static_cast<long>(now - lastCo2Ms),
      lastRespirationMs == 0 ? -1L : static_cast<long>(now - lastRespirationMs),
      lastHeartMs == 0 ? -1L : static_cast<long>(now - lastHeartMs),
      lastPresenceMs == 0 ? -1L : static_cast<long>(now - lastPresenceMs),
      breathPhase, lastPhaseMs == 0 ? -1L : static_cast<long>(now - lastPhaseMs),
      static_cast<unsigned long>(phaseSequence),
      static_cast<unsigned long>(mmWaveUpdateSuccesses),
      static_cast<unsigned long>(mmWave.framesParsed()),
      lastMmWaveUpdateMs == 0 ? -1L : static_cast<long>(now - lastMmWaveUpdateMs),
      static_cast<unsigned>(mmWaveSerial.available()),
      static_cast<unsigned long>(mmWaveUpdateMisses));

  diagPrintf(
      "[health] co2     model=%s identity=%s preheat=%d uart_ppm=%u event_id=%lu "
      "req=%lu accepted=%lu csum_fail=%lu hdr_fail=%lu timeout=%lu short=%lu "
      "resync=%lu range_rej=%lu txn=%s uart1_pending=%u\n",
      CO2_SENSOR_MODEL, CO2_EVENT_IDENTITY_CLASS, co2ModelPreheatDone(now) ? 0 : 1,
      static_cast<unsigned>(co2LastUartPpm),
      static_cast<unsigned long>(co2MeasurementEventId),
      static_cast<unsigned long>(co2RequestsSent),
      static_cast<unsigned long>(co2AcceptedSamples),
      static_cast<unsigned long>(co2ChecksumFailures),
      static_cast<unsigned long>(co2HeaderFailures),
      static_cast<unsigned long>(co2TimeoutFailures),
      static_cast<unsigned long>(co2ShortFrameFailures),
      static_cast<unsigned long>(co2ResyncEvents),
      static_cast<unsigned long>(co2RangeRejects),
      mhz19Txn == Mhz19Txn::AWAIT_RESPONSE ? "AWAIT" : "IDLE",
      static_cast<unsigned>(mhz19Serial.available()));

  logAiReadiness(now);

  // min_heap 이 중요한 값입니다. 순간값은 이미 회복된 뒤라 무선 송신 붕괴
  // 시점의 ~40 KB 딥이 안 보입니다.
  diagPrintf(
      "[health] sys     heap=%lu min_heap=%lu max_alloc=%lu reclaim=%lu "
      "reclaim_skip_tcp=%lu holdoff=%d backoff_ms=%lu loop_iters=%lu "
      "netlog=%d sent=%lu dropped=%lu\n",
      static_cast<unsigned long>(ESP.getFreeHeap()),
      static_cast<unsigned long>(ESP.getMinFreeHeap()),
      static_cast<unsigned long>(ESP.getMaxAllocHeap()),
      static_cast<unsigned long>(heapReclaims),
      static_cast<unsigned long>(heapReclaimSkippedTcp),
      udpHoldoffActive(now) ? 1 : 0, static_cast<unsigned long>(udpBackoffMs),
      static_cast<unsigned long>(loopIterations), diagUdpEnabled ? 1 : 0,
      static_cast<unsigned long>(diagUdpLinesSent),
      static_cast<unsigned long>(diagUdpLinesDropped));
}

// 절대값은 "한 번이라도 있었나", 비율은 "지금 일어나고 있나"에 답합니다.
// READY 가 계속 HIGH 로 붙은 상태와 정상 1 fps 를 가르는 건 두 번째 질문뿐입니다.
void logLinkDiagnostics(uint32_t now) {
  static uint32_t lastSampleMs = 0;
  static uint32_t lastLoops = 0;
  static uint32_t lastAttempts = 0;
  static uint32_t lastFrames = 0;
  static uint32_t lastDatagrams = 0;
  static uint32_t lastBytes = 0;

  const bool due = scheduleDue(now, lastLinkLogMs, DIAG_LOG_PERIOD_MS);
  if (!linkDiagnosticsOnce && !(due && linkDiagnosticsEnabled)) return;
  linkDiagnosticsOnce = false;

  const uint32_t windowMs = lastSampleMs == 0
                                ? DIAG_LOG_PERIOD_MS
                                : static_cast<uint32_t>(now - lastSampleMs);
  const uint32_t divisor = windowMs == 0 ? 1 : windowMs;
  const uint32_t datagrams = udpDatagramsSent;
  const uint32_t bytes = udpBytesSent;

  diagPrintf(
      "[link] up_s=%lu loop_hz=%lu ready_pin=%lu ready_i2c=%lu cap_hz=%lu "
      "frame_hz=%lu cap_max_ms=%lu udp_on=%d cap_on=%d udp_hz=%lu udp_kbps=%lu "
      "udp_dg_max_ms=%lu udp_frame_max_ms=%lu udp_slow=%lu udp_fail=%lu "
      "preempt=%lu suppress=%lu defer=%lu udp_restarts=%lu tcp_sess=%lu "
      "drops=%lu peer_closed=%lu sent=%lu gap_max_ms=%lu gap_warn=%lu "
      "gap_late=%lu write_max_ms=%lu slow_w=%lu stalls=%lu partial=%lu "
      "mutex_max_ms=%lu mutex_to=%lu tcp_errno=%ld udp_errno=%ld rssi=%d "
      "heap=%lu min_heap=%lu max_alloc=%lu holdoff=%d backoff_ms=%lu\n",
      static_cast<unsigned long>(now / 1000),
      static_cast<unsigned long>((loopIterations - lastLoops) * 1000UL / divisor),
      static_cast<unsigned long>(thermalReadyByPin),
      static_cast<unsigned long>(thermalReadyByI2c),
      static_cast<unsigned long>((thermalCaptureAttempts - lastAttempts) * 1000UL /
                                 divisor),
      static_cast<unsigned long>((thermalSequence - lastFrames) * 1000UL / divisor),
      static_cast<unsigned long>(thermalCaptureMaxMs), thermalUdpEnabled ? 1 : 0,
      thermalCaptureEnabled ? 1 : 0,
      static_cast<unsigned long>((datagrams - lastDatagrams) * 1000UL / divisor),
      static_cast<unsigned long>((bytes - lastBytes) * 8UL / divisor),
      static_cast<unsigned long>(udpDatagramMaxMs),
      static_cast<unsigned long>(udpFrameMaxMs),
      static_cast<unsigned long>(udpSlowDatagrams),
      static_cast<unsigned long>(thermalUdpSendFailures),
      static_cast<unsigned long>(thermalFramesPreempted),
      static_cast<unsigned long>(thermalFramesSuppressed),
      static_cast<unsigned long>(thermalFramesDeferred),
      static_cast<unsigned long>(udpSocketRestarts),
      static_cast<unsigned long>(tcpSessions), static_cast<unsigned long>(tcpDrops),
      static_cast<unsigned long>(tcpPeerClosed),
      static_cast<unsigned long>(telemetryPacketsSent),
      static_cast<unsigned long>(telemetryGapMaxMs),
      static_cast<unsigned long>(telemetryGapOverWarn),
      static_cast<unsigned long>(telemetryGapOverDeadline),
      static_cast<unsigned long>(tcpWriteMaxMs),
      static_cast<unsigned long>(tcpSlowWrites),
      static_cast<unsigned long>(tcpWriteStalls),
      static_cast<unsigned long>(tcpPartialWrites),
      static_cast<unsigned long>(tcpMutexWaitMaxMs),
      static_cast<unsigned long>(tcpMutexTimeouts), static_cast<long>(tcpLastErrno),
      static_cast<long>(udpLastErrno), static_cast<int>(WiFi.RSSI()),
      static_cast<unsigned long>(ESP.getFreeHeap()),
      static_cast<unsigned long>(ESP.getMinFreeHeap()),
      static_cast<unsigned long>(ESP.getMaxAllocHeap()),
      udpHoldoffActive(now) ? 1 : 0, static_cast<unsigned long>(udpBackoffMs));

  lastSampleMs = now;
  lastLoops = loopIterations;
  lastAttempts = thermalCaptureAttempts;
  lastFrames = thermalSequence;
  lastDatagrams = datagrams;
  lastBytes = bytes;
}

// =============================================================================
// 시리얼 콘솔
// =============================================================================
void printThermalHeaderDump() {
  Serial.printf("[thermal] last header words[0..15]:");
  for (uint8_t i = 0; i < 16; ++i) {
    Serial.printf(" [%u]=%u", static_cast<unsigned>(i),
                  static_cast<unsigned>(thermalLastHeader[i]));
  }
  Serial.println();
  Serial.printf(
      "[thermal] layout=%s min_index=%d max_index=%d probes=%u mismatches=%lu "
      "flat=%lu strict=%d\n",
      thermalHeaderLayoutResolved ? "resolved"
                                  : (thermalHeaderLayoutGiveUp ? "unresolved"
                                                               : "probing"),
      static_cast<int>(thermalHeaderMinIndex), static_cast<int>(thermalHeaderMaxIndex),
      static_cast<unsigned>(thermalHeaderProbes),
      static_cast<unsigned long>(thermalHeaderMismatches),
      static_cast<unsigned long>(thermalFlatFrames),
      THERMAL_STRICT_VALIDATION ? 1 : 0);
}

void printDiagnosticHelp() {
  Serial.println(
      "[help] 시리얼 명령: u=thermal UDP 송신 토글, c=thermal 캡처 토글, "
      "s=[link] 즉시 출력, l=주기 [link] 토글, t=[tx] JSON 로그 토글, "
      "j=마지막 JSON 즉시 출력, d=thermal 헤더 덤프, i=I2C 재스캔, "
      "p=CO2 모델예열 강제완료, "
      "r=진단 카운터 리셋, h=도움말");
  Serial.printf(
      "[help] Pi 수신 데드라인: runtime gateway=5000 ms. 이 노드는 gap_ms>=%lu "
      "에서 경고하고 TCP write 는 %lu ms 에서 fail-fast 합니다.\n",
      static_cast<unsigned long>(TELEMETRY_GAP_WARN_MS),
      static_cast<unsigned long>(TCP_WRITE_DEADLINE_MS));
  Serial.println(
      "[help] 캡처 vs UDP 분리: 'c' 다음 'u' 로 cap_on=0/udp_on=0 -> "
      "cap_on=1/udp_on=0 -> cap_on=1/udp_on=1 순으로 돌려보고 [link] 의 "
      "write_max_ms, gap_max_ms, udp_errno, heap, holdoff 를 보세요.");
}

void resetDiagnosticCounters() {
  tcpSessions = 0; tcpDrops = 0; tcpShortSessions = 0; tcpPeerClosed = 0;
  tcpWriteStalls = 0; tcpPartialWrites = 0; tcpMutexTimeouts = 0;
  tcpMutexWaitMaxMs = 0; tcpMutexWaitSlow = 0; tcpWriteMaxMs = 0;
  tcpSlowWrites = 0; telemetryGapMaxMs = 0; telemetryGapOverWarn = 0;
  telemetryGapOverDeadline = 0; telemetryPacketsSent = 0;
  udpDatagramsSent = 0; udpBytesSent = 0; udpDatagramMaxMs = 0;
  udpSlowDatagrams = 0; udpFrameMaxMs = 0; thermalFramesSuppressed = 0;
  thermalFramesDeferred = 0; thermalTcpYields = 0; heapReclaims = 0;
  heapReclaimSkippedTcp = 0; udpHoldoffEvents = 0; udpHoldoffUntilMs = 0;
  udpBackoffMs = 0; tcpWriteTimeouts = 0; udpSocketRestarts = 0;
  tcpLastErrno = 0; udpLastErrno = 0;
  thermalCaptureAttempts = 0; thermalReadyByPin = 0; thermalReadyByI2c = 0;
  thermalCaptureMaxMs = 0; thermalHeaderMismatches = 0; thermalFlatFrames = 0;
  co2ChecksumFailures = 0; co2HeaderFailures = 0; co2TimeoutFailures = 0;
  co2ShortFrameFailures = 0; co2ResyncEvents = 0; co2RangeRejects = 0;
  mmWaveUpdateMisses = 0;
  // 와이어에서 보이는 상태(telemetrySequence, thermalSequence)는 건드리지
  // 않습니다. Pi 는 한 연결 안에서 뒤로 가는 sequence 를 거부합니다.
}

void handleSerialCommand() {
  while (Serial.available() > 0) {
    switch (Serial.read()) {
      case 'u': case 'U':
        thermalUdpEnabled = !thermalUdpEnabled;
        Serial.printf("[cmd] thermal UDP %s cap_on=%d udp_on=%d\n",
                      thermalUdpEnabled ? "ENABLED" : "DISABLED",
                      thermalCaptureEnabled ? 1 : 0, thermalUdpEnabled ? 1 : 0);
        break;
      case 'c': case 'C':
        thermalCaptureEnabled = !thermalCaptureEnabled;
        Serial.printf("[cmd] thermal capture %s cap_on=%d udp_on=%d\n",
                      thermalCaptureEnabled ? "ENABLED" : "DISABLED",
                      thermalCaptureEnabled ? 1 : 0, thermalUdpEnabled ? 1 : 0);
        break;
      case 'r': case 'R':
        resetDiagnosticCounters();
        Serial.println("[cmd] diagnostic counters cleared");
        break;
      case 's': case 'S':
        linkDiagnosticsOnce = true;
        break;
      case 'l': case 'L':
        linkDiagnosticsEnabled = !linkDiagnosticsEnabled;
        Serial.printf("[cmd] periodic [link] %s\n",
                      linkDiagnosticsEnabled ? "ENABLED" : "DISABLED");
        break;
      case 't': case 'T':
        txLogEnabled = !txLogEnabled;
        Serial.printf("[cmd] [tx]/[why] logging %s\n",
                      txLogEnabled ? "ENABLED" : "DISABLED");
        break;
      case 'j': case 'J':
        if (lastTelemetryJsonLength == 0) {
          Serial.println("[cmd] 아직 전송된 JSON 이 없습니다");
        } else {
          Serial.printf("[cmd] last json: %s\n", lastTelemetryJson);
        }
        break;
      case 'd': case 'D':
        printThermalHeaderDump();
        break;
      case 'i': case 'I':
        scanI2cBus();
        break;
      case 'p': case 'P':
        co2ModelPreheatForced = true;
        Serial.println(
            "[cmd] CO2 모델 예열을 강제 완료 처리했습니다. 시연용입니다 - "
            "Winsen 3분 예열 전 값은 정확도가 보장되지 않습니다.");
        break;
      case 'n': case 'N':
        diagUdpEnabled = !diagUdpEnabled;
        Serial.printf("[cmd] 진단 로그 Wi-Fi 미러 %s (UDP :%u 브로드캐스트)\n",
                      diagUdpEnabled ? "ENABLED" : "DISABLED",
                      static_cast<unsigned>(DIAG_LOG_UDP_PORT));
        break;
      case 'h': case 'H': case '?':
        printDiagnosticHelp();
        break;
      default:
        break;  // 개행과 잡바이트 무시
    }
  }
}

// =============================================================================
// 부팅 자가진단
// =============================================================================
void runSelfTest() {
  Serial.println("[selftest] ---- 부팅 자가진단 ----");

  scanI2cBus();

  // MR60: 라이브러리 시작 후 UART2 로 바이트가 들어오는지 본다.
  const uint32_t mmStart = millis();
  uint32_t mmBytes = 0;
  while (static_cast<uint32_t>(millis() - mmStart) < 1500) {
    mmBytes += mmWaveSerial.available();
    mmWave.update(0);
    vTaskDelay(pdMS_TO_TICKS(10));
  }
  Serial.printf("[selftest] mmwave  uart2(RX=%d,TX=%d) bytes_seen=%lu frames=%lu -> %s\n",
                PIN_MMWAVE_RX, PIN_MMWAVE_TX, static_cast<unsigned long>(mmBytes),
                static_cast<unsigned long>(mmWave.framesParsed()),
                mmWave.framesParsed() > 0
                    ? "OK"
                    : (mmBytes > 0 ? "바이트는 오는데 파싱 안 됨(보레이트/배선 확인)"
                                   : "FAIL: 데이터 없음 (TX/RX 교차, 5V 전원 확인)"));

  // MH-Z19B: 즉시 한 번 물어본다.
  resetMhz19Rx();
  mhz19Serial.write(MHZ19_READ_CMD, sizeof(MHZ19_READ_CMD));
  mhz19Serial.flush();
  const uint32_t co2Start = millis();
  uint8_t got = 0;
  uint8_t probe[16] = {};
  while (static_cast<uint32_t>(millis() - co2Start) < 1000 && got < 9) {
    while (mhz19Serial.available() > 0 && got < sizeof(probe)) {
      probe[got++] = static_cast<uint8_t>(mhz19Serial.read());
    }
    vTaskDelay(pdMS_TO_TICKS(10));
  }
  if (got >= 9 && probe[0] == 0xFF && probe[1] == 0x86) {
    const uint16_t ppm = (static_cast<uint16_t>(probe[2]) << 8) | probe[3];
    Serial.printf(
        "[selftest] co2     uart1(RX=%d,TX=%d) OK ppm=%u checksum=%s "
        "(예열 %lu s 동안은 telemetry 에 null 로 나갑니다)\n",
        PIN_MHZ19_RX, PIN_MHZ19_TX, static_cast<unsigned>(ppm),
        mhz19Checksum(probe) == probe[8] ? "ok" : "MISMATCH",
        static_cast<unsigned long>(CO2_MODEL_PREHEAT_MS / 1000));
  } else {
    Serial.printf(
        "[selftest] co2     uart1(RX=%d,TX=%d) FAIL bytes=%u first=%02X %02X "
        "-> MH-Z19B TX->GPIO%d, RX->GPIO%d 교차 배선과 5V(4.5~5.5V) 전원, "
        "9600 8N1 을 확인하세요\n",
        PIN_MHZ19_RX, PIN_MHZ19_TX, static_cast<unsigned>(got), probe[0], probe[1],
        PIN_MHZ19_RX, PIN_MHZ19_TX);
  }
  resetMhz19Rx();

  // PIR: 현재 레벨.
  Serial.printf("[selftest] pir     GPIO%d level=%d (지금 움직이면 바뀌어야 정상)\n",
                PIN_PIR, digitalRead(PIN_PIR));

  // Thermal.
  Serial.printf(
      "[selftest] thermal started=%d addr=0x%02X ready_mode=%s -> %s\n",
      thermalStarted ? 1 : 0, static_cast<unsigned>(thermalAddress),
      thermalReadyModeText(thermalReadyMode),
      thermalStarted ? "OK" : "FAIL: I2C/전원/RESET(GPIO25) 확인");

  Serial.println("[selftest] ---- 끝 ----");
}

// =============================================================================
// setup / loop
// =============================================================================
void setup() {
  Serial.begin(USB_BAUD);
  setupWait(500);
  Serial.println("\nSafeNest ESP32 sensor node v3 (field bring-up) 시작");
  initializeBootId();
  Serial.printf("[identity] device=%s boot=%s firmware=%s diag=%s reset=%d\n",
                DEVICE_ID, bootId, NODE_FIRMWARE_VERSION, DIAGNOSTIC_BUILD_ID,
                static_cast<int>(esp_reset_reason()));
  Serial.printf(
      "[config] telemetry=%lums co2_sample=%lums thermal_divider=%u "
      "strict_thermal=%d rpi=%s:%u thermal_udp=%u\n",
      static_cast<unsigned long>(TELEMETRY_PERIOD_MS),
      static_cast<unsigned long>(CO2_UART_SAMPLE_PERIOD_MS),
      static_cast<unsigned>(THERMAL_FRAME_RATE_DIVIDER),
      THERMAL_STRICT_VALIDATION ? 1 : 0, RPI_HOST,
      static_cast<unsigned>(RPI_PORT), static_cast<unsigned>(THERMAL_UDP_PORT));
  printDiagnosticHelp();

  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_THERMAL_CS, OUTPUT);
  digitalWrite(PIN_THERMAL_CS, HIGH);
  pinMode(PIN_THERMAL_READY, INPUT);
  pinMode(PIN_THERMAL_RESET, OUTPUT);
  digitalWrite(PIN_THERMAL_RESET, HIGH);

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.setClock(100000);
  thermalSpi.begin(PIN_THERMAL_SCLK, PIN_THERMAL_MISO, PIN_THERMAL_MOSI,
                   PIN_THERMAL_CS);

  // setPins() 를 라이브러리 begin() 앞에 두어야 core 2.x/3.x 모두에서
  // 핀 없는 Serial.begin() 이 GPIO16/17 을 유지합니다.
  mmWaveSerial.setPins(PIN_MMWAVE_RX, PIN_MMWAVE_TX);
  mmWave.begin(&mmWaveSerial, MMWAVE_BAUD, 0);

  // UART1 은 MH-Z19B. setPins() 를 begin() 앞에 두지 않으면 core 가 WROOM
  // 플래시 핀 9/10 을 잡습니다.
  mhz19Serial.setPins(PIN_MHZ19_RX, PIN_MHZ19_TX);
  mhz19Serial.begin(MHZ19_BAUD);
  mhz19Serial.setTimeout(0);

  telemetryQueue = xQueueCreate(1, sizeof(TelemetrySnapshot));
  thermalQueue = xQueueCreate(1, sizeof(ThermalTxFrame));
  networkEvents = xEventGroupCreate();
  networkTxMutex = xSemaphoreCreateMutex();
  if (telemetryQueue == nullptr || thermalQueue == nullptr ||
      networkEvents == nullptr || networkTxMutex == nullptr) {
    Serial.println("[fatal] 큐/동기화 객체 할당 실패");
    while (true) vTaskDelay(portMAX_DELAY);
  }

  initializeThermalCamera();
  runSelfTest();

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // 연속 thermal 스트림을 위한 지연 최소화
  for (const WifiCredential &entry : WIFI_NETWORKS) {
    wifiMulti.addAP(entry.ssid, entry.password);
    Serial.printf("[wifi] 후보 등록: %s\n", entry.ssid);
  }
  wifiMulti.run(8000);
  Serial.printf("[wifi] 연결됨: %s  ip=%s  rssi=%d\n",
                WiFi.SSID().c_str(), WiFi.localIP().toString().c_str(),
                static_cast<int>(WiFi.RSSI()));
  // mDNS 응답기. Pi 를 이름으로 찾기 위해 필요하고, 이 노드도 esp32-01.local
  // 로 보이게 되어 반대 방향 진단도 쉬워집니다.
  if (MDNS.begin("safenest-esp32")) {
    Serial.println("[mdns] responder 시작 (이 노드: safenest-esp32.local)");
  }
  Serial.printf(
      "[netlog] 진단 로그를 UDP :%u 브로드캐스트로도 보냅니다. USB 없이 외부 "
      "전원으로 돌릴 때 같은 Wi-Fi 의 PC 에서 그대로 볼 수 있습니다.\n",
      static_cast<unsigned>(DIAG_LOG_UDP_PORT));

  // 우선순위만으로는 lwIP 가 이미 큐에 넣은 datagram 을 선점할 수 없습니다.
  // 그래서 datagram 단위 뮤텍스와 TCP critical bit 가 여전히 필요합니다.
  xTaskCreatePinnedToCore(telemetryTcpTask, "telemetry-tcp", 8192, nullptr, 2,
                          nullptr, 0);
  xTaskCreatePinnedToCore(thermalUdpTask, "thermal-udp", 8192, nullptr, 1, nullptr,
                          0);
}

void loop() {
  const uint32_t now = millis();
  ++loopIterations;

  pollMmWave(now);
  pollCo2(now);
  captureThermalIfReady(now);
  // SPI 캡처가 UART 서비스를 막습니다. 프레임 중간 SOF 가 다음 ~1 fps 카메라
  // 틱까지 Seeed 어셈블러에 남지 않도록 한 번 더 비웁니다.
  pollMmWave(millis());

  if (scheduleDue(now, lastPirPollMs, PIR_PERIOD_MS)) {
    pirMotion = digitalRead(PIN_PIR) == HIGH;
  }

  publishTelemetrySnapshot(now);
  handleSerialCommand();
  logTransmittedTelemetry(now);
  logLinkDiagnostics(now);
  logHealth(now);

  // 협조적 양보만. 런타임에는 의도적으로 delay() 가 없습니다.
  taskYIELD();
}
