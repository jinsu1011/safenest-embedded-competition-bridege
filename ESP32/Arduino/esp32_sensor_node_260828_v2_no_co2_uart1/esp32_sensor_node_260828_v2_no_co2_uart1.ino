/*
 * SafeNest ESP32 sensor node
 *
 * Sensors:
 *   - Seeed MR60BHA2 (UART): respiration and heart rate
 *   - CO2: not connected (UART1 is reserved for a future sensor)
 *   - PIR (digital input): motion
 *   - Waveshare Thermal Camera HAT / MI48xx (I2C control + SPI data): 80 x 62
 *
 * Transport:
 *   - TCP for low-rate mmWave/CO2/PIR JSON telemetry
 *   - Chunked UDP for big-endian uint16 Thermal frames
 *
 * The Arduino loop never calls delay(). Sensor scheduling uses millis().
 * TCP reconnect/writes and Thermal UDP writes run in separate FreeRTOS tasks.
 * If the network is slow, the one-slot thermal queue keeps only the newest frame.
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
#include "Seeed_Arduino_mmWave.h"
#include "secrets.h"

// -----------------------------------------------------------------------------
// Device identity. Wi-Fi and Raspberry Pi settings live in ignored secrets.h.
// ----------------------------------------------------------------------------
constexpr char DEVICE_ID[] = "esp32-01";
char bootId[33] = {};
constexpr uint16_t THERMAL_UDP_PORT = 5005;

// -----------------------------------------------------------------------------
// ESP32 Dev Module wiring (matches the existing standalone sensor tests).
// ----------------------------------------------------------------------------
constexpr int PIN_I2C_SDA = 21;
constexpr int PIN_I2C_SCL = 22;
constexpr int PIN_PIR = 13;
constexpr int PIN_MMWAVE_RX = 16;  // ESP32 RX <- MR60BHA2 TX
constexpr int PIN_MMWAVE_TX = 17;  // ESP32 TX -> MR60BHA2 RX

// Reserved for a future UART1 CO2 sensor. UART1 is deliberately not started
// while the sensor is absent, so these pins remain electrically inactive.
constexpr int PIN_CO2_UART_RX = 32;  // ESP32 RX1 <- future CO2 TX
constexpr int PIN_CO2_UART_TX = 33;  // ESP32 TX1 -> future CO2 RX

constexpr int PIN_THERMAL_SCLK = 18;
constexpr int PIN_THERMAL_MISO = 19;
constexpr int PIN_THERMAL_MOSI = 23;
constexpr int PIN_THERMAL_CS = 27;
constexpr int PIN_THERMAL_READY = 26;
constexpr int PIN_THERMAL_RESET = 25;

constexpr uint32_t USB_BAUD = 115200;
constexpr uint32_t MMWAVE_BAUD = 115200;
constexpr uint32_t THERMAL_SPI_HZ = 8000000;

// Runtime schedules.
constexpr uint32_t PIR_PERIOD_MS = 20;
// One scalar snapshot per second is sufficient for the default LCD display.
// TCP writes remain isolated in their own task.
constexpr uint32_t TELEMETRY_PERIOD_MS = 1000;
constexpr uint32_t HEALTH_LOG_PERIOD_MS = 10000;
constexpr uint32_t MMWAVE_STALE_MS = 10000;
constexpr uint32_t CO2_STALE_MS = 15000;
// The MR60 reports 0x0F09 occupancy on its own cadence, independent of the
// respiration/heart-rate stream. This bound only has to outlive normal report
// gaps; once it lapses the field goes null (unknown), which suppresses mmWave
// inference rather than asserting an empty room.
constexpr uint32_t PRESENCE_MAX_AGE_MS = 5000;
constexpr char NODE_FIRMWARE_VERSION[] =
    "safenest-esp32-sensor-node/1.6.1-no-co2-chunk-yield.1";
constexpr char DIAGNOSTIC_BUILD_ID[] = "no-co2-chunk-yield-20260901-01";

// -----------------------------------------------------------------------------
// Link diagnostics.
//
// A "disconnect" on this link is really a missed receive deadline on the Pi.
// Both receivers close the socket themselves when one packet does not arrive
// in time, and neither waits as long as this node is willing to stall:
//
//   RaspberryPi/LCD/server.py             connection.settimeout(2.0). Its
//                                         header recv is wrapped in
//                                         `except socket.timeout: continue`,
//                                         but the payload recv is not, so one
//                                         2 s gap between the 16-byte header
//                                         and the JSON body raises
//                                         socket.timeout -- an OSError, which
//                                         its handler treats as fatal.
//   RaspberryPi/Runtime/gateway/          5 s total deadline per field.
//     receiver.py
//
// writeAll() below tolerates a 5000 ms stall, longer than either deadline, so
// this node can call a write successful long after the Pi has hung up. Every
// counter here answers one question: did a telemetry packet reach the wire
// inside the Pi's tolerance, and if not, which stage consumed the time --
// queue wait, TX-mutex wait, or the socket write itself.
// ----------------------------------------------------------------------------
constexpr uint32_t PI_PACKET_DEADLINE_MS = 2000;
// Warn below the Pi deadline so the log shows the approach, not only the crash.
constexpr uint32_t TELEMETRY_GAP_WARN_MS = 1500;
constexpr uint32_t TCP_WRITE_WARN_MS = 150;
constexpr uint32_t TCP_MUTEX_WARN_MS = 100;
// beginTcpCritical() waited with portMAX_DELAY, which makes a stalled UDP
// datagram indistinguishable from an idle link: the TCP task simply never
// returns and nothing is logged. A bounded wait turns that invisible hang into
// a counted, timestamped event.
constexpr uint32_t TCP_MUTEX_MAX_WAIT_MS = 3000;
constexpr uint32_t UDP_DATAGRAM_WARN_MS = 40;
// 2 ms between chunks was only a CPU yield. Nine 1200-byte datagrams still
// hit the radio in ~34 ms, which is what filled the lwIP pool (errno 12) and
// left no airtime for the 1 Hz TCP write. 20 ms is long enough for the TCP
// task to wake, take the mutex, and finish a ~3 ms write, and 8 gaps stay
// inside the ~480 ms 2 fps period and the Pi's 500 ms thermal reassembly
// window (measured from the last chunk, not the first).
constexpr uint32_t UDP_CHUNK_GAP_MS = 20;
// A live telemetry write holds TCP_CRITICAL_BIT for a few milliseconds.
// Waiting this out and then continuing the same frame is the interleave;
// returning Preempted used to drop the remaining chunks. Connect() holds the
// bit much longer, but tcpLinkHealthy is already false then, so we stand down
// instead of waiting out the handshake.
constexpr uint32_t UDP_YIELD_TO_TCP_MAX_MS = 80;
// udpStarted was only cleared when Wi-Fi dropped, so once sendto() entered a
// failing state the task retried the same socket forever: udp_sent froze at 61
// for the rest of the run while udp_failed kept climbing. Rebuilding the socket
// after a run of failures gives the transmitter a way back without a reboot.
constexpr uint32_t UDP_MAX_CONSECUTIVE_FAILURES = 10;
// The per-2-second [link] firehose was 38 fields on one line, five times more
// often than [health]. Same cadence as [health] keeps it readable; 's' still
// prints one on demand and 'l' silences the periodic copy.
constexpr uint32_t DIAG_LOG_PERIOD_MS = 10000;

// -----------------------------------------------------------------------------
// Thermal-camera constants (MI48xx + MI0801/MI0802, 80 x 62).
// ----------------------------------------------------------------------------
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
constexpr size_t THERMAL_PIXEL_COUNT = THERMAL_WIDTH * THERMAL_HEIGHT;
constexpr size_t THERMAL_HEADER_WORDS = THERMAL_WIDTH;
constexpr size_t THERMAL_CAPTURE_WORDS =
    THERMAL_HEADER_WORDS + THERMAL_PIXEL_COUNT;

// Set divisor 12: for a 25 FPS sensor this requests about 2.08 FPS.
// Lowering this value raises bandwidth and ESP32 CPU/SPI load.
//
// Divisor 4 (6.25 FPS) is what the Wi-Fi TX path could not sustain: one frame
// is 9 datagrams, so 6.25 FPS put ~57 datagrams/s and ~64 KB/s on the radio in
// 160 ms bursts. Under that load udp_sent froze mid-run while udp_failed kept
// climbing, free heap fell ~40 KB, and TCP connect stopped completing its
// handshake -- every attempt burned the full 1500 ms timeout -- until a reboot.
// The same run with the thermal camera unpowered held tcp_connection_failures
// at 0 with connect_ms=12. 12 keeps the frame format identical at one third the
// bandwidth; raise it back only with the [link] udp_kbps and tcp drop counters
// in view.
constexpr uint8_t THERMAL_FRAME_RATE_DIVIDER = 12;

// -----------------------------------------------------------------------------
// SafeNest TCP protocol v1 for scalar telemetry.
// Outer header (16 bytes, network byte order):
//   magic[4]="SNST", version:u8, type:u8, flags:u16,
//   packet_sequence:u32, payload_length:u32
// Packet type 1 payload: UTF-8 JSON.
// Thermal UDP logical payload: 16-byte metadata followed by 4960 uint16 words.
// -----------------------------------------------------------------------------
constexpr uint8_t PROTOCOL_VERSION = 1;
constexpr uint8_t PACKET_TELEMETRY_JSON = 1;
constexpr uint8_t PACKET_THERMAL_U16_BE = 2;
constexpr size_t PACKET_HEADER_SIZE = 16;
constexpr size_t THERMAL_META_SIZE = 16;

// SafeNest Thermal UDP v1. A 1200-byte datagram stays below the common
// Ethernet/Wi-Fi MTU after IPv4 and UDP headers, avoiding IP fragmentation.
// Header fields are network byte order and every chunk repeats the frame CRC32.
constexpr char THERMAL_UDP_MAGIC[] = "SNTU";
constexpr uint8_t THERMAL_UDP_VERSION = 1;
constexpr size_t THERMAL_UDP_HEADER_SIZE = 32;
constexpr size_t THERMAL_UDP_DATAGRAM_SIZE = 1200;
constexpr size_t THERMAL_UDP_CHUNK_SIZE =
    THERMAL_UDP_DATAGRAM_SIZE - THERMAL_UDP_HEADER_SIZE;
constexpr size_t THERMAL_PAYLOAD_SIZE =
    THERMAL_META_SIZE + THERMAL_PIXEL_COUNT * sizeof(uint16_t);
constexpr uint16_t THERMAL_UDP_CHUNK_COUNT =
    (THERMAL_PAYLOAD_SIZE + THERMAL_UDP_CHUNK_SIZE - 1) /
    THERMAL_UDP_CHUNK_SIZE;

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
  // Tri-state MR60 occupancy. `humanDetectedKnown == false` must serialize as
  // JSON null, never false: the Pi presence gate treats false as "room empty"
  // and would then suppress mmWave inference for the wrong reason.
  bool humanDetectedRaw;
  bool humanDetectedKnown;
};

struct ThermalTxFrame {
  uint32_t frameSequence;
  uint32_t uptimeMs;
  uint16_t minimumRaw;
  uint16_t maximumRaw;
  uint16_t pixels[THERMAL_PIXEL_COUNT];
};

// Per-write forensics. A bare bool made a 2 ms success and a 4.9 s stall that
// eventually succeeded look identical, yet only the second one outlives the
// Pi's receive timeout and gets the socket closed underneath us.
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
  // The Serial kill switch dropped the frame. Kept distinct from Preempted so
  // a deliberate A/B test never inflates the contention counter.
  Suppressed,
  // The TCP session is down, so the transmitter yielded the radio to let it
  // reconnect. Distinct from Suppressed because nobody asked for it, and from
  // Preempted because no TCP write was actually waiting on the mutex.
  Deferred,
};

HardwareSerial mmWaveSerial(2);
HardwareSerial co2Serial(1);  // Reserved; begin() is not called in this build.

// The library's own SEEED_MR60BHA2::isHumanDetected() cannot express "unknown":
// it returns false both when the room is empty and when no 0x0F09 report has
// been parsed yet, and it self-clears its validity flag on read. Overriding
// handleType() captures the report itself, so an absent report stays
// distinguishable from a negative one. The base implementation is still
// invoked, leaving library state untouched, and the base class has already
// verified both frame checksums before dispatching here.
class SafeNestMR60BHA2 : public SEEED_MR60BHA2 {
 public:
  bool handleType(uint16_t type, const uint8_t *data,
                  size_t dataLength) override {
    if (type == static_cast<uint16_t>(
                    TypeHeartBreath::ReportHumanDetection)) {
      // The vendor handler reads data[0] unguarded; refuse a truncated report
      // here instead of letting it read out of bounds.
      if (dataLength < 1) return false;
      presenceRaw_ = data[0] != 0;
      presencePending_ = true;
    }
    return SEEED_MR60BHA2::handleType(type, data, dataLength);
  }

  // Same one-shot out-parameter idiom as getBreathRate()/getHeartRate(): the
  // return value means "a new report was parsed", never "nobody is present".
  bool takePresence(bool &value) {
    if (!presencePending_) return false;
    presencePending_ = false;
    value = presenceRaw_;
    return true;
  }

 private:
  bool presenceRaw_ = false;
  bool presencePending_ = false;
};

SafeNestMR60BHA2 mmWave;
SPIClass thermalSpi(VSPI);

QueueHandle_t telemetryQueue = nullptr;
QueueHandle_t thermalQueue = nullptr;
EventGroupHandle_t networkEvents = nullptr;
SemaphoreHandle_t networkTxMutex = nullptr;
constexpr EventBits_t TCP_CRITICAL_BIT = BIT0;

uint16_t thermalCapture[THERMAL_CAPTURE_WORDS];
// These ~10 KiB objects are global on purpose. Keeping either on a task stack
// can overflow the default Arduino loop stack on a non-PSRAM ESP32.
ThermalTxFrame thermalProducerFrame;
ThermalTxFrame thermalNetworkFrame;
uint8_t thermalAddress = 0;
bool thermalStarted = false;

float respirationRate = NAN;
float heartRate = NAN;
uint16_t co2Ppm = 0;
bool pirMotion = false;
bool humanDetectedRaw = false;

uint32_t lastRespirationMs = 0;
uint32_t lastHeartMs = 0;
uint32_t lastPresenceMs = 0;
uint32_t lastCo2Ms = 0;
uint32_t lastThermalStatusPollMs = 0;
uint32_t lastPirPollMs = 0;
uint32_t lastTelemetryMs = 0;
uint32_t lastHealthLogMs = 0;
uint32_t telemetrySequence = 0;
uint32_t thermalSequence = 0;
uint32_t thermalCrcErrors = 0;
uint32_t thermalRangeErrors = 0;
// Written by the network tasks on core 0 and read by loop() on core 1. Each
// counter has exactly one writer and aligned 32-bit accesses are atomic on
// Xtensa, so volatile only has to stop the compiler caching them in registers.
volatile uint32_t telemetryQueueOverwrites = 0;
volatile uint32_t thermalQueueOverwrites = 0;
volatile uint32_t tcpConnectionFailures = 0;
volatile uint32_t tcpSendFailures = 0;
volatile uint32_t thermalUdpFramesSent = 0;
volatile uint32_t thermalFramesPreempted = 0;
volatile uint32_t thermalTcpYields = 0;
volatile uint32_t thermalUdpSendFailures = 0;

// Link diagnostics written by the network tasks on core 0, under the same
// single-writer, aligned-32-bit rule as the counters above.
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

// Set by the TCP task around a live session and read by the thermal task.
// Single writer, aligned 32-bit access, same rule as the counters above.
//
// This is the back-pressure signal. TCP telemetry is the contract with the Pi;
// thermal is best-effort. While the session is down the transmit path is either
// saturated or the link is bad, and a continuous thermal stream is precisely
// what keeps a SYN from completing -- so the thermal task stands down until the
// session is back rather than competing with the reconnect it is blocking.
volatile bool tcpLinkHealthy = false;

// Runtime A/B switches driven from the Serial console. Toggling the thermal
// transmitter without reflashing is the shortest path to proving whether the
// UDP stream is what breaks the TCP stream.
volatile bool thermalUdpEnabled = true;
volatile bool thermalCaptureEnabled = true;

// Written and read only by loop() on core 1, so volatile is not warranted.
uint32_t thermalCaptureAttempts = 0;
uint32_t thermalReadyByPin = 0;
uint32_t thermalReadyByI2c = 0;
uint32_t thermalCaptureMaxMs = 0;
uint32_t loopIterations = 0;
uint32_t lastLinkLogMs = 0;
// [link] is a 38-field diagnostic line. Useful during a bisect, unreadable as a
// permanent fixture, so the periodic copy can be silenced ('l') without losing
// the on-demand one ('s').
bool linkDiagnosticsEnabled = true;
bool linkDiagnosticsOnce = false;
uint32_t thermalStatusQueryFailures = 0;
uint32_t mmWaveUpdateSuccesses = 0;
uint32_t mmWaveUpdateMisses = 0;
uint32_t lastMmWaveUpdateMs = 0;
uint8_t thermalUdpDatagram[THERMAL_UDP_DATAGRAM_SIZE];

// Wrap-safe periodic scheduling helper. Updating by period, rather than assigning
// now, avoids gradual drift. A long overrun is collapsed to one execution.
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

void initializeBootId() {
  uint32_t words[4];
  for (uint8_t index = 0; index < 4; ++index) words[index] = esp_random();
  snprintf(bootId, sizeof(bootId), "%08lx%08lx%08lx%08lx",
           static_cast<unsigned long>(words[0]),
           static_cast<unsigned long>(words[1]),
           static_cast<unsigned long>(words[2]),
           static_cast<unsigned long>(words[3]));
}

// Blocking waits are used only during one-time hardware initialization. The
// runtime loop itself remains delay-free.
void setupWait(uint32_t milliseconds) {
  vTaskDelay(pdMS_TO_TICKS(milliseconds));
}

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
  if (Wire.requestFrom(thermalAddress, static_cast<uint8_t>(1)) != 1) {
    return false;
  }
  value = Wire.read();
  return true;
}

void initializeThermalCamera() {
  if (i2cPresent(THERMAL_ADDRESS_A)) {
    thermalAddress = THERMAL_ADDRESS_A;
  } else if (i2cPresent(THERMAL_ADDRESS_B)) {
    thermalAddress = THERMAL_ADDRESS_B;
  } else {
    Serial.println("[thermal] ERROR: I2C address 0x40/0x41 not found");
    return;
  }

  // Active-low reset. The pulse and post-reset wait are required by hardware.
  digitalWrite(PIN_THERMAL_RESET, LOW);
  delayMicroseconds(100);
  digitalWrite(PIN_THERMAL_RESET, HIGH);
  setupWait(100);

  uint8_t evkTest = 0;
  if (!thermalReadRegister(REG_EVK_TEST, evkTest)) {
    Serial.println("[thermal] ERROR: register read failed");
    return;
  }

  // Non-bridge MI48 variants require the explicit sensor power-up command.
  if (evkTest != 0xFF) {
    if (!thermalWriteRegister(REG_SENSOR_POWERUP, 0x13)) {
      Serial.println("[thermal] ERROR: power-up command failed");
      return;
    }
    setupWait(100);
  }

  const uint32_t bootStarted = millis();
  uint8_t status = STATUS_BOOTING;
  while (static_cast<uint32_t>(millis() - bootStarted) < 3000) {
    if (!thermalReadRegister(REG_STATUS, status)) {
      Serial.println("[thermal] ERROR: status read failed");
      return;
    }
    if ((status & STATUS_BOOTING) == 0) break;
    setupWait(25);
  }
  if (status & STATUS_BOOTING) {
    Serial.println("[thermal] ERROR: boot timeout");
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
    Serial.println("[thermal] ERROR: continuous stream start failed");
    return;
  }

  thermalStarted = true;
  Serial.printf("[thermal] ready: addr=0x%02X type=%u fw=%u.%u.%u\n",
                static_cast<unsigned>(thermalAddress),
                static_cast<unsigned>(sensorType),
                static_cast<unsigned>((fw1 >> 4) & 0x0F),
                static_cast<unsigned>(fw1 & 0x0F),
                static_cast<unsigned>(fw2));
}

// MI48 frame CRC: CRC-16/CCITT-FALSE, polynomial 0x1021, initial 0xFFFF.
// The vendor driver calculates it over the native uint16 pixel buffer, so
// each received word is fed low byte first and then high byte.
uint16_t thermalFrameCrc(const uint16_t *pixels, size_t count) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < count; ++i) {
    const uint8_t bytes[2] = {
        static_cast<uint8_t>(pixels[i] & 0xFF),
        static_cast<uint8_t>(pixels[i] >> 8)};
    for (uint8_t value : bytes) {
      crc ^= static_cast<uint16_t>(value) << 8;
      for (uint8_t bit = 0; bit < 8; ++bit) {
        crc = (crc & 0x8000) ? static_cast<uint16_t>((crc << 1) ^ 0x1021)
                             : static_cast<uint16_t>(crc << 1);
      }
    }
  }
  return crc;
}

bool thermalDataReady(uint32_t now) {
  // Counted per source: a READY line left floating, or driven permanently
  // high, reports ready on every one of the ~40k loop iterations per second
  // and would flood the UDP path with garbage frames. Comparing ready_pin
  // against the ~6 accepted frames per second is what makes that visible.
  if (digitalRead(PIN_THERMAL_READY) == HIGH) {
    ++thermalReadyByPin;
    return true;
  }

  // I2C polling is a fallback and also makes a disconnected READY wire visible.
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

void captureThermalIfReady(uint32_t now) {
  if (!thermalStarted || !thermalCaptureEnabled) return;
  if (!thermalDataReady(now)) return;

  ++thermalCaptureAttempts;
  const uint32_t captureStartedMs = millis();

  thermalSpi.beginTransaction(
      SPISettings(THERMAL_SPI_HZ, MSBFIRST, SPI_MODE0));
  digitalWrite(PIN_THERMAL_CS, LOW);
  delayMicroseconds(100);

  // MI48xx returns every word MSB first. Reading bytes explicitly avoids host
  // endianness ambiguity in SPI.transfer16().
  for (size_t i = 0; i < THERMAL_CAPTURE_WORDS; ++i) {
    const uint8_t highByte = thermalSpi.transfer(0x00);
    const uint8_t lowByte = thermalSpi.transfer(0x00);
    thermalCapture[i] = (static_cast<uint16_t>(highByte) << 8) | lowByte;
  }

  delayMicroseconds(100);
  digitalWrite(PIN_THERMAL_CS, HIGH);
  thermalSpi.endTransaction();

  // 10080 single-byte SPI transfers block loop() outright. If this grows past
  // the telemetry period it starves publishTelemetrySnapshot() on core 1, which
  // the Pi sees as a late packet just as surely as a stalled socket write.
  const uint32_t captureMs =
      static_cast<uint32_t>(millis() - captureStartedMs);
  if (captureMs > thermalCaptureMaxMs) thermalCaptureMaxMs = captureMs;

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

  const uint16_t expectedCrc = thermalCapture[7];
  const uint16_t actualCrc = thermalFrameCrc(
      thermalCapture + THERMAL_HEADER_WORDS, THERMAL_PIXEL_COUNT);
  if (actualCrc != expectedCrc) {
    ++thermalCrcErrors;
    if (thermalCrcErrors <= 3 || thermalCrcErrors % 25 == 0) {
      Serial.printf(
          "[thermal] dropped CRC frame: header=0x%04X calc=0x%04X "
          "errors=%lu\n",
          static_cast<unsigned>(expectedCrc),
          static_cast<unsigned>(actualCrc),
          static_cast<unsigned long>(thermalCrcErrors));
    }
    return;
  }

  if (thermalCapture[5] != frame.maximumRaw ||
      thermalCapture[6] != frame.minimumRaw) {
    ++thermalRangeErrors;
    if (thermalRangeErrors <= 3 || thermalRangeErrors % 25 == 0) {
      Serial.printf(
          "[thermal] dropped header-range frame: header=%u..%u "
          "calc=%u..%u errors=%lu\n",
          static_cast<unsigned>(thermalCapture[6]),
          static_cast<unsigned>(thermalCapture[5]),
          static_cast<unsigned>(frame.minimumRaw),
          static_cast<unsigned>(frame.maximumRaw),
          static_cast<unsigned long>(thermalRangeErrors));
    }
    return;
  }

  frame.frameSequence = ++thermalSequence;
  // Queue length is one, so this replaces an unsent old frame under congestion.
  xQueueOverwrite(thermalQueue, &frame);
}

void pollCo2Uart(uint32_t now) {
  (void)now;
  // Intentionally empty: no CO2 sensor is connected in this build.
  // Future UART1 integration point:
  //   1. Call co2Serial.begin(sensorBaud, SERIAL_8N1,
  //                          PIN_CO2_UART_RX, PIN_CO2_UART_TX) in setup().
  //   2. Parse complete sensor frames here without delay().
  //   3. After validating a reading, assign co2Ppm and lastCo2Ms = now.
}

void pollMmWave(uint32_t now) {
  // timeout=0 makes the library consume currently buffered UART data without
  // waiting. Repeated loop calls drain all queued radar frames.
  if (!mmWave.update(0)) {
    ++mmWaveUpdateMisses;
    return;
  }
  ++mmWaveUpdateSuccesses;
  lastMmWaveUpdateMs = now;

  float value = 0.0f;
  if (mmWave.getBreathRate(value) && isfinite(value)) {
    respirationRate = value;
    lastRespirationMs = now;
  }
  if (mmWave.getHeartRate(value) && isfinite(value)) {
    heartRate = value;
    lastHeartMs = now;
  }

  // MR60's own normalized occupancy boolean. It is recorded verbatim: no
  // occupancy threshold is derived from breath rate or any other signal, and
  // no majority-vote smoothing is applied, because the wire contract carries
  // human_detected_raw only. Staleness is judged at publish time so a radar
  // that stops reporting eventually degrades this to null.
  bool presenceValue = false;
  if (mmWave.takePresence(presenceValue)) {
    humanDetectedRaw = presenceValue;
    lastPresenceMs = now;
  }
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
  snapshot.respirationValid = isFresh(lastRespirationMs, now, MMWAVE_STALE_MS);
  snapshot.heartValid = isFresh(lastHeartMs, now, MMWAVE_STALE_MS);
  // The UART1 CO2 sensor is not connected, so this build always publishes
  // co2_ppm=null and valid.co2=false while preserving the receiver schema.
  snapshot.co2Valid = false;
  // isFresh() also rejects the never-observed case (lastPresenceMs == 0), so a
  // node whose radar never reported occupancy publishes null rather than false.
  snapshot.humanDetectedRaw = humanDetectedRaw;
  snapshot.humanDetectedKnown = isFresh(lastPresenceMs, now,
                                        PRESENCE_MAX_AGE_MS);
  xQueueOverwrite(telemetryQueue, &snapshot);
}

// Big-endian integer encoders keep the protocol independent of CPU endianness.
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

void makePacketHeader(uint8_t *header, uint8_t type, uint32_t sequence,
                      uint32_t payloadLength) {
  memcpy(header, "SNST", 4);
  header[4] = PROTOCOL_VERSION;
  header[5] = type;
  putU16(header + 6, 0);  // flags: reserved for protocol v1
  putU32(header + 8, sequence);
  putU32(header + 12, payloadLength);
}

// Runs only in the network task, so a slow peer can never stall sensor capture.
bool writeAll(WiFiClient &client, const uint8_t *data, size_t length,
              TcpWriteReport &report) {
  constexpr size_t CHUNK_BYTES = 512;
  constexpr uint32_t TIMEOUT_MS = 5000;

  report = TcpWriteReport{};
  size_t sent = 0;
  const uint32_t startedMs = millis();
  uint32_t lastProgress = startedMs;

  while (sent < length) {
    if (!client.connected()) {
      report.bytesWritten = sent;
      report.elapsedMs = static_cast<uint32_t>(millis() - startedMs);
      report.connectedAtEnd = false;
      return false;
    }

    const size_t remaining = length - sent;
    const size_t chunk =
        remaining > CHUNK_BYTES ? CHUNK_BYTES : remaining;
    errno = 0;
    const size_t written = client.write(data + sent, chunk);

    if (written > 0) {
      if (written < chunk) ++report.partialWrites;
      sent += written;
      lastProgress = millis();
    } else {
      // A zero-length write means lwIP had no TX buffer for this segment. That
      // buffer pool is shared with the thermal UDP stream, so counting these
      // separates "the socket died" from "the radio was busy sending frames".
      ++report.zeroWrites;
      report.lastErrno = errno;
      const uint32_t stallMs = static_cast<uint32_t>(millis() - lastProgress);
      if (stallMs > report.longestStallMs) report.longestStallMs = stallMs;
      if (stallMs > TIMEOUT_MS) {
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

// The mutex wait is the ESP32-side price of the thermal stream: precisely the
// time this task spends unable to touch the socket because a UDP datagram is
// in flight. Reporting it turns "the connection dropped" into a number.
bool beginTcpCritical(uint32_t &waitMs) {
  const uint32_t startedMs = millis();
  xEventGroupSetBits(networkEvents, TCP_CRITICAL_BIT);
  const bool acquired =
      xSemaphoreTake(networkTxMutex, pdMS_TO_TICKS(TCP_MUTEX_MAX_WAIT_MS)) ==
      pdTRUE;
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

void formatNullableFloat(char *output, size_t outputSize, bool valid,
                         float value) {
  if (valid && isfinite(value)) {
    const int written = snprintf(output, outputSize, "%.2f", value);
    // A truncated number stays syntactically valid JSON but carries the wrong
    // magnitude, so fail closed to null rather than publish it.
    if (written > 0 && static_cast<size_t>(written) < outputSize) return;
  }
  strlcpy(output, "null", outputSize);
}

bool sendTelemetry(WiFiClient &client, const TelemetrySnapshot &snapshot,
                   size_t &payloadLength, TcpWriteReport &report) {
  payloadLength = 0;
  report = TcpWriteReport{};
  char respiration[20], heart[20], co2[6];
  formatNullableFloat(respiration, sizeof(respiration),
                      snapshot.respirationValid, snapshot.respirationRate);
  formatNullableFloat(heart, sizeof(heart), snapshot.heartValid,
                      snapshot.heartRate);
  if (snapshot.co2Valid) {
    snprintf(co2, sizeof(co2), "%u", static_cast<unsigned>(snapshot.co2Ppm));
  } else {
    strlcpy(co2, "null", sizeof(co2));
  }

  const char *humanDetectedText = snapshot.humanDetectedKnown
                                      ? (snapshot.humanDetectedRaw ? "true"
                                                                   : "false")
                                      : "null";

  // The LCD telemetry contract stays intentionally small. Diagnostics remain
  // available through the rate-limited Serial health log below.
  char json[512];
  const int length = snprintf(
      json, sizeof(json),
      "{\"schema\":\"safenest.telemetry.v1\",\"device_id\":\"%s\","
      "\"boot_id\":\"%s\",\"seq\":%lu,\"uptime_ms\":%lu,"
      "\"resp_rate_bpm\":%s,\"heart_rate_bpm\":%s,\"co2_ppm\":%s,"
      "\"pir_motion\":%s,"
      "\"valid\":{\"respiration\":%s,\"heart\":%s,\"co2\":%s},"
      "\"mmwave\":{\"human_detected_raw\":%s}}",
      DEVICE_ID, bootId, static_cast<unsigned long>(snapshot.sequence),
      static_cast<unsigned long>(snapshot.uptimeMs), respiration, heart, co2,
      snapshot.pirMotion ? "true" : "false",
      snapshot.respirationValid ? "true" : "false",
      snapshot.heartValid ? "true" : "false",
      snapshot.co2Valid ? "true" : "false", humanDetectedText);
  if (length <= 0 || static_cast<size_t>(length) >= sizeof(json)) return false;

  payloadLength = static_cast<size_t>(length);
  uint8_t packet[PACKET_HEADER_SIZE + sizeof(json)];
  makePacketHeader(packet, PACKET_TELEMETRY_JSON, snapshot.sequence,
                   static_cast<uint32_t>(length));
  memcpy(packet + PACKET_HEADER_SIZE, json, payloadLength);

  return writeAll(client, packet, PACKET_HEADER_SIZE + payloadLength, report);
}

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

// Rate-limited: Serial.printf() blocks for roughly 90 us per character at
// 115200 baud, so an unthrottled warning would itself become the stall it is
// trying to report.
void logSlowDatagram(uint32_t frameSequence, uint16_t chunkIndex,
                     uint32_t durationMs) {
  static uint32_t lastLogMs = 0;
  const uint32_t now = millis();
  if (lastLogMs != 0 && static_cast<uint32_t>(now - lastLogMs) < 1000) return;
  lastLogMs = now;
  Serial.printf(
      "[udp-slow] frame=%lu chunk=%u sendto_ms=%lu errno=%ld -- the TCP task "
      "cannot send for this long\n",
      static_cast<unsigned long>(frameSequence),
      static_cast<unsigned>(chunkIndex),
      static_cast<unsigned long>(durationMs),
      static_cast<long>(udpLastErrno));
}

// Park this task until TCP is not in a write/connect, without holding the TX
// mutex. The higher-priority TCP task can then take the mutex and send. false
// means the remaining chunks of this frame should be abandoned.
bool yieldRadioToTcp(uint32_t maxWaitMs) {
  const uint32_t startedMs = millis();
  bool waited = false;
  for (;;) {
    if (!tcpLinkHealthy) return false;
    if ((xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) == 0) {
      if (waited) thermalTcpYields = thermalTcpYields + 1;
      return true;
    }
    if (static_cast<uint32_t>(millis() - startedMs) >= maxWaitMs) {
      return false;
    }
    waited = true;
    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

ThermalSendResult sendThermalUdp(WiFiUDP &udp,
                                 const ThermalTxFrame &frame) {
  constexpr TickType_t MUTEX_TIMEOUT = pdMS_TO_TICKS(1000);
  // Runtime kill switch. Dropping the frame here rather than upstream leaves
  // capture, CRC checking and queueing byte-for-byte identical, so toggling it
  // isolates the network transmit path and nothing else.
  if (!thermalUdpEnabled) return ThermalSendResult::Suppressed;
  // Back-pressure, checked before the CRC32 pass so a deferred frame costs
  // nothing: 9936 bytes of table-free CRC is not free at 2 fps, and there is no
  // point spending it on a frame that will not be sent.
  if (!tcpLinkHealthy) return ThermalSendResult::Deferred;
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
    // TCP set the bit and is blocked on this mutex. Sending now would jump
    // the queue; give it back and retry the same chunk after the write.
    if ((xEventGroupGetBits(networkEvents) & TCP_CRITICAL_BIT) != 0) {
      xSemaphoreGive(networkTxMutex);
      continue;
    }

    // Timed inside the mutex, because this is exactly the window during which
    // the TCP task is locked out. Under Wi-Fi TX-buffer exhaustion sendto()
    // blocks rather than failing, so the duration matters more than the return
    // value: a datagram that takes 400 ms still reports sent=true while having
    // pushed the telemetry packet 400 ms closer to the Pi's deadline.
    errno = 0;
    const uint32_t datagramStartedMs = millis();
    const bool sent =
        udp.beginPacket(RPI_HOST, THERMAL_UDP_PORT) &&
        udp.write(thermalUdpDatagram, THERMAL_UDP_HEADER_SIZE + length) ==
            THERMAL_UDP_HEADER_SIZE + length &&
        udp.endPacket() == 1;
    const uint32_t datagramMs =
        static_cast<uint32_t>(millis() - datagramStartedMs);
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

// Every socket teardown funnels through here, so a reconnect is never silent.
// The counters are sampled at the instant of the drop, which is what makes them
// attributable: a gap_max_ms at or above PI_PACKET_DEADLINE_MS means this node
// missed the Pi's receive deadline, and the Pi closed first.
void logTcpDrop(const char *reason, uint32_t sessionStartedMs,
                uint32_t sessionPackets, int pendingRxBytes) {
  const uint32_t now = millis();
  const uint32_t sessionMs =
      sessionStartedMs == 0 ? 0
                            : static_cast<uint32_t>(now - sessionStartedMs);
  tcpDrops = tcpDrops + 1;
  if (sessionMs < 10000) tcpShortSessions = tcpShortSessions + 1;
  Serial.printf(
      "[tcp-drop] reason=%s session_ms=%lu session_packets=%lu "
      "since_last_send_ms=%ld gap_max_ms=%lu gap_late=%lu write_max_ms=%lu "
      "write_stalls=%lu partial_writes=%lu mutex_max_ms=%lu mutex_to=%lu "
      "tcp_errno=%ld rx_pending=%d udp_on=%d udp_dg=%lu udp_slow=%lu "
      "udp_dg_max_ms=%lu udp_frame_max_ms=%lu udp_errno=%ld rssi=%d "
      "heap=%lu min_heap=%lu drops=%lu short_sessions=%lu\n",
      reason,
      static_cast<unsigned long>(sessionMs),
      static_cast<unsigned long>(sessionPackets),
      lastTelemetrySentMs == 0
          ? -1L
          : static_cast<long>(now - lastTelemetrySentMs),
      static_cast<unsigned long>(telemetryGapMaxMs),
      static_cast<unsigned long>(telemetryGapOverDeadline),
      static_cast<unsigned long>(tcpWriteMaxMs),
      static_cast<unsigned long>(tcpWriteStalls),
      static_cast<unsigned long>(tcpPartialWrites),
      static_cast<unsigned long>(tcpMutexWaitMaxMs),
      static_cast<unsigned long>(tcpMutexTimeouts),
      static_cast<long>(tcpLastErrno),
      pendingRxBytes,
      thermalUdpEnabled ? 1 : 0,
      static_cast<unsigned long>(udpDatagramsSent),
      static_cast<unsigned long>(udpSlowDatagrams),
      static_cast<unsigned long>(udpDatagramMaxMs),
      static_cast<unsigned long>(udpFrameMaxMs),
      static_cast<long>(udpLastErrno),
      static_cast<int>(WiFi.RSSI()),
      static_cast<unsigned long>(ESP.getFreeHeap()),
      static_cast<unsigned long>(ESP.getMinFreeHeap()),
      static_cast<unsigned long>(tcpDrops),
      static_cast<unsigned long>(tcpShortSessions));
}

void telemetryTcpTask(void *parameter) {
  (void)parameter;
  WiFiClient client;
  TelemetrySnapshot telemetry{};
  uint32_t lastDequeuedSequence = 0;
  uint32_t lastNetworkLogMs = 0;
  uint32_t lastConnectDurationMs = 0;
  uint32_t lastQueueWaitMs = 0;
  uint32_t lastMutexWaitMs = 0;
  uint32_t sessionStartedMs = 0;
  uint32_t sessionPackets = 0;
  bool sessionOpen = false;

  for (;;) {
    uint32_t mutexWaitMs = 0;

    if (WiFi.status() != WL_CONNECTED) {
      tcpLinkHealthy = false;
      if (sessionOpen) {
        logTcpDrop("wifi_down", sessionStartedMs, sessionPackets,
                   client.available());
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
      // Stand the thermal transmitter down for the whole reconnect, not just
      // for the connect() call: the radio has to be quiet for the handshake to
      // complete, and TCP_CRITICAL_BIT only covers the moments this task holds
      // the mutex.
      tcpLinkHealthy = false;
      // Arriving here with sessionOpen still set means the peer closed or reset
      // the socket while this node believed the link was healthy. That is the
      // signature of a Pi-side receive timeout rather than a local send error,
      // so it is counted separately from write_failed.
      if (sessionOpen) {
        tcpPeerClosed = tcpPeerClosed + 1;
        logTcpDrop("peer_closed", sessionStartedMs, sessionPackets,
                   client.available());
        sessionOpen = false;
      }
      Serial.printf("[network] connecting to %s:%u\n", RPI_HOST, RPI_PORT);
      bool connected = false;
      if (beginTcpCritical(mutexWaitMs)) {
        const uint32_t connectStartedMs = millis();
        errno = 0;
        connected = client.connect(RPI_HOST, RPI_PORT, 1500);
        lastConnectDurationMs = millis() - connectStartedMs;
        if (!connected) {
          tcpLastErrno = errno;
          client.stop();
        }
        endTcpCritical();
      } else {
        tcpMutexTimeouts = tcpMutexTimeouts + 1;
      }
      if (!connected) {
        tcpConnectionFailures = tcpConnectionFailures + 1;
        Serial.printf(
            "[tcp-connect-fail] mutex_wait_ms=%lu connect_ms=%lu errno=%ld "
            "failures=%lu\n",
            static_cast<unsigned long>(mutexWaitMs),
            static_cast<unsigned long>(lastConnectDurationMs),
            static_cast<long>(tcpLastErrno),
            static_cast<unsigned long>(tcpConnectionFailures));
        vTaskDelay(pdMS_TO_TICKS(1000));
        continue;
      }
      client.setNoDelay(true);
      sessionStartedMs = millis();
      sessionPackets = 0;
      sessionOpen = true;
      tcpLinkHealthy = true;
      tcpSessions = tcpSessions + 1;
      Serial.printf(
          "[tcp-open] session=%lu connect_ms=%lu mutex_wait_ms=%lu rssi=%d "
          "heap=%lu\n",
          static_cast<unsigned long>(tcpSessions),
          static_cast<unsigned long>(lastConnectDurationMs),
          static_cast<unsigned long>(mutexWaitMs),
          static_cast<int>(WiFi.RSSI()),
          static_cast<unsigned long>(ESP.getFreeHeap()));
    }

    // Scalar telemetry has priority and is small.
    if (xQueueReceive(telemetryQueue, &telemetry, 0) == pdTRUE) {
      telemetryQueueOverwrites = telemetryQueueOverwrites +
                                 telemetry.sequence - lastDequeuedSequence - 1;
      lastDequeuedSequence = telemetry.sequence;
      // The producer stamps uptimeMs from the same millis() clock on core 1,
      // so this difference is how long the snapshot waited for the network
      // task. It separates "loop() published late" from "the socket was slow".
      lastQueueWaitMs =
          static_cast<uint32_t>(millis() - telemetry.uptimeMs);

      size_t jsonPayloadLength = 0;
      bool sent = false;
      // Distinguishes "the packet never reached the socket" from "the socket
      // is gone". A mutex timeout is the first: it leaves the connection fully
      // intact, so none of the teardown below may run for it. Only the write
      // path calls client.stop(), and only that ends the session.
      bool socketClosedByFailure = false;
      uint32_t writeDurationMs = 0;
      TcpWriteReport report{};
      if (beginTcpCritical(mutexWaitMs)) {
        const uint32_t writeStartedMs = millis();
        sent = sendTelemetry(client, telemetry, jsonPayloadLength, report);
        writeDurationMs = millis() - writeStartedMs;
        if (!sent) {
          tcpLastErrno = report.lastErrno;
          client.stop();
          socketClosedByFailure = true;
        }
        endTcpCritical();
        if (writeDurationMs > tcpWriteMaxMs) tcpWriteMaxMs = writeDurationMs;
        if (writeDurationMs >= TCP_WRITE_WARN_MS) {
          tcpSlowWrites = tcpSlowWrites + 1;
        }
        if (report.zeroWrites > 0) tcpWriteStalls = tcpWriteStalls + 1;
        if (report.partialWrites > 0) tcpPartialWrites = tcpPartialWrites + 1;
      } else {
        tcpMutexTimeouts = tcpMutexTimeouts + 1;
        Serial.printf(
            "[tcp-blocked] seq=%lu mutex_wait_ms=%lu timeouts=%lu -- the "
            "thermal UDP task held the TX mutex past the limit, so this "
            "telemetry packet never reached the socket\n",
            static_cast<unsigned long>(telemetry.sequence),
            static_cast<unsigned long>(mutexWaitMs),
            static_cast<unsigned long>(tcpMutexTimeouts));
      }
      lastMutexWaitMs = mutexWaitMs;

      if (!sent) {
        // Counted either way: this snapshot did not reach the Pi. Which of the
        // two causes it was is already on the console -- [tcp-send-fail] here,
        // or [tcp-blocked] above.
        tcpSendFailures = tcpSendFailures + 1;
      }

      if (socketClosedByFailure) {
        // client.stop() ran above, so the socket is gone. Drop the signal here
        // rather than waiting for the next loop to notice, so the thermal task
        // is quiet before the reconnect starts. The reconnect path is also the
        // only place that sets tcpLinkHealthy back to true, which is why this
        // must never fire while the connection is still usable.
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
            static_cast<long>(report.lastErrno),
            report.connectedAtEnd ? 1 : 0,
            static_cast<unsigned long>(tcpSendFailures));
        if (sessionOpen) {
          logTcpDrop("write_failed", sessionStartedMs, sessionPackets, 0);
          sessionOpen = false;
        }
      }

      if (sent) {
        // On-wire cadence as the Pi experiences it. The receiver closes the
        // socket when a packet does not complete inside its own timeout, so
        // this gap -- not the send-failure count -- is the quantity that
        // predicts a disconnect. It is measured after the write completes,
        // which is the moment the last byte was handed to lwIP.
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
                "[tcp-gap] seq=%lu gap_ms=%lu pi_deadline_ms=%lu "
                "queue_wait_ms=%lu mutex_wait_ms=%lu write_ms=%lu "
                "stall_ms=%lu zero_writes=%u overwrites=%lu udp_on=%d "
                "udp_dg_max_ms=%lu rssi=%d%s\n",
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
                gapMs >= PI_PACKET_DEADLINE_MS ? "  <<< EXCEEDS_PI_DEADLINE"
                                               : "");
          }
        }
        lastTelemetrySentMs = completedMs;
        telemetryPacketsSent = telemetryPacketsSent + 1;
        ++sessionPackets;
      }

      const uint32_t now = millis();
      if (lastNetworkLogMs == 0 ||
          static_cast<uint32_t>(now - lastNetworkLogMs) >=
              HEALTH_LOG_PERIOD_MS) {
        Serial.printf(
            "[network] tcp connect_ms=%lu write_ms=%lu queue_wait_ms=%lu "
            "mutex_wait_ms=%lu seq=%lu json_bytes=%u gap_max_ms=%lu "
            "tcp_send_failures=%lu thermal_preemptions=%lu "
            "thermal_udp_failures=%lu\n",
            static_cast<unsigned long>(lastConnectDurationMs),
            static_cast<unsigned long>(writeDurationMs),
            static_cast<unsigned long>(lastQueueWaitMs),
            static_cast<unsigned long>(lastMutexWaitMs),
            static_cast<unsigned long>(telemetry.sequence),
            static_cast<unsigned>(jsonPayloadLength),
            static_cast<unsigned long>(telemetryGapMaxMs),
            static_cast<unsigned long>(tcpSendFailures),
            static_cast<unsigned long>(thermalFramesPreempted),
            static_cast<unsigned long>(thermalUdpSendFailures));
        lastNetworkLogMs = now;
      }

      if (!sent) {
        continue;
      }
    }

    vTaskDelay(pdMS_TO_TICKS(2));
  }
}

void thermalUdpTask(void *parameter) {
  (void)parameter;
  WiFiUDP udp;
  bool udpStarted = false;
  uint32_t lastDequeuedSequence = 0;
  uint32_t consecutiveFailures = 0;
  for (;;) {
    if (WiFi.status() != WL_CONNECTED) {
      if (udpStarted) {
        udp.stop();
        udpStarted = false;
      }
      vTaskDelay(pdMS_TO_TICKS(50));
      continue;
    }
    if (!udpStarted) {
      udpStarted = udp.begin(0);
      if (!udpStarted) {
        vTaskDelay(pdMS_TO_TICKS(250));
        continue;
      }
    }
    if (xQueueReceive(thermalQueue, &thermalNetworkFrame, 0) == pdTRUE) {
      thermalQueueOverwrites = thermalQueueOverwrites +
                               thermalNetworkFrame.frameSequence -
                               lastDequeuedSequence - 1;
      lastDequeuedSequence = thermalNetworkFrame.frameSequence;
      // Wall time for the whole 9-datagram frame. Compared against the 480 ms
      // budget of a 2.08 fps stream (THERMAL_FRAME_RATE_DIVIDER = 12), this
      // says whether the transmitter is keeping up or saturating the radio.
      const uint32_t frameStartedMs = millis();
      const ThermalSendResult result =
          sendThermalUdp(udp, thermalNetworkFrame);
      const uint32_t frameMs =
          static_cast<uint32_t>(millis() - frameStartedMs);
      if (frameMs > udpFrameMaxMs) udpFrameMaxMs = frameMs;
      switch (result) {
        case ThermalSendResult::Sent:
          thermalUdpFramesSent = thermalUdpFramesSent + 1;
          consecutiveFailures = 0;
          break;
        case ThermalSendResult::Preempted:
          thermalFramesPreempted = thermalFramesPreempted + 1;
          break;
        case ThermalSendResult::Failed:
          thermalUdpSendFailures = thermalUdpSendFailures + 1;
          ++consecutiveFailures;
          if (thermalUdpSendFailures <= 3 ||
              thermalUdpSendFailures % 25 == 0) {
            Serial.printf(
                "[udp-fail] frame=%lu frame_ms=%lu errno=%ld failures=%lu "
                "consecutive=%lu\n",
                static_cast<unsigned long>(
                    thermalNetworkFrame.frameSequence),
                static_cast<unsigned long>(frameMs),
                static_cast<long>(udpLastErrno),
                static_cast<unsigned long>(thermalUdpSendFailures),
                static_cast<unsigned long>(consecutiveFailures));
          }
          // A run this long is a stuck socket, not congestion: sendto() has
          // returned an error every time since the last success. Rebuild it.
          if (consecutiveFailures >= UDP_MAX_CONSECUTIVE_FAILURES) {
            udp.stop();
            udpStarted = false;
            consecutiveFailures = 0;
            udpSocketRestarts = udpSocketRestarts + 1;
            Serial.printf(
                "[udp-restart] socket rebuilt after %lu consecutive failures "
                "errno=%ld restarts=%lu\n",
                static_cast<unsigned long>(UDP_MAX_CONSECUTIVE_FAILURES),
                static_cast<long>(udpLastErrno),
                static_cast<unsigned long>(udpSocketRestarts));
          }
          break;
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

// Grouped subsystem lines rather than one 30-field, ~470-character line. Every
// field the single-line form carried is still here, under the subsystem that
// owns it, plus the three that were missing when it mattered most: the node's
// own IP, the RSSI, and the minimum free heap.
void logHealth(uint32_t now) {
  if (!scheduleDue(now, lastHealthLogMs, HEALTH_LOG_PERIOD_MS)) return;

  const bool wifiUp = WiFi.status() == WL_CONNECTED;
  const IPAddress ip = WiFi.localIP();

  Serial.printf("[health] ===== up=%lus =====\n",
                static_cast<unsigned long>(now / 1000));

  // localIP() answers what the old line could not: whether this node is even on
  // the subnet RPI_HOST lives on. Without it a wrong-subnet run reads exactly
  // like a dead Pi -- repeated "connecting to", no other evidence either way.
  Serial.printf(
      "[health] link    wifi=%s ip=%u.%u.%u.%u rssi=%d rpi=%s:%u tcp=%s\n",
      wifiUp ? "up" : "down", static_cast<unsigned>(ip[0]),
      static_cast<unsigned>(ip[1]), static_cast<unsigned>(ip[2]),
      static_cast<unsigned>(ip[3]),
      wifiUp ? static_cast<int>(WiFi.RSSI()) : 0, RPI_HOST,
      static_cast<unsigned>(RPI_PORT), tcpLinkHealthy ? "up" : "down");

  Serial.printf(
      "[health] tcp     conn_fail=%lu send_fail=%lu queue_ovw=%lu\n",
      static_cast<unsigned long>(tcpConnectionFailures),
      static_cast<unsigned long>(tcpSendFailures),
      static_cast<unsigned long>(telemetryQueueOverwrites));

  Serial.printf(
      "[health] thermal frames=%lu udp_sent=%lu udp_fail=%lu preempt=%lu "
      "yield=%lu defer=%lu restarts=%lu crc_err=%lu rng_err=%lu status_fail=%lu "
      "queue_ovw=%lu\n",
      static_cast<unsigned long>(thermalSequence),
      static_cast<unsigned long>(thermalUdpFramesSent),
      static_cast<unsigned long>(thermalUdpSendFailures),
      static_cast<unsigned long>(thermalFramesPreempted),
      static_cast<unsigned long>(thermalTcpYields),
      static_cast<unsigned long>(thermalFramesDeferred),
      static_cast<unsigned long>(udpSocketRestarts),
      static_cast<unsigned long>(thermalCrcErrors),
      static_cast<unsigned long>(thermalRangeErrors),
      static_cast<unsigned long>(thermalStatusQueryFailures),
      static_cast<unsigned long>(thermalQueueOverwrites));

  Serial.printf(
      "[health] sensors resp=%.1f heart=%.1f co2=null pir=%d co2_age_ms=%ld "
      "mmw_ok=%lu mmw_age_ms=%ld mmw_uart=%u mmw_miss=%lu\n",
      respirationRate, heartRate, pirMotion ? 1 : 0,
      lastCo2Ms == 0 ? -1L : static_cast<long>(now - lastCo2Ms),
      static_cast<unsigned long>(mmWaveUpdateSuccesses),
      lastMmWaveUpdateMs == 0
          ? -1L
          : static_cast<long>(now - lastMmWaveUpdateMs),
      static_cast<unsigned>(mmWaveSerial.available()),
      static_cast<unsigned long>(mmWaveUpdateMisses));

  Serial.printf(
      "[health] co2     disabled uart=1 initialized=0 rx=%d tx=%d\n",
      PIN_CO2_UART_RX, PIN_CO2_UART_TX);

  // min_heap is the one that matters here: the transmit-path collapse showed up
  // as a ~40 KB dip that the instantaneous value had already recovered from by
  // the time the next line printed.
  Serial.printf("[health] sys     heap=%lu min_heap=%lu\n",
                static_cast<unsigned long>(ESP.getFreeHeap()),
                static_cast<unsigned long>(ESP.getMinFreeHeap()));
}

// Absolute counters answer "did it ever happen"; rates answer "is it happening
// now". Only the second question separates a healthy 2 fps thermal stream from
// a READY line stuck high that captures and transmits thousands of times per
// second.
void logLinkDiagnostics(uint32_t now) {
  static uint32_t lastSampleMs = 0;
  static uint32_t lastLoops = 0;
  static uint32_t lastAttempts = 0;
  static uint32_t lastFrames = 0;
  static uint32_t lastDatagrams = 0;
  static uint32_t lastBytes = 0;

  // scheduleDue() runs unconditionally so the window baselines below stay
  // anchored to a real interval even while the periodic copy is silenced.
  const bool due = scheduleDue(now, lastLinkLogMs, DIAG_LOG_PERIOD_MS);
  if (!linkDiagnosticsOnce && !(due && linkDiagnosticsEnabled)) return;
  linkDiagnosticsOnce = false;

  const uint32_t windowMs =
      lastSampleMs == 0 ? DIAG_LOG_PERIOD_MS
                        : static_cast<uint32_t>(now - lastSampleMs);
  const uint32_t divisor = windowMs == 0 ? 1 : windowMs;
  const uint32_t datagrams = udpDatagramsSent;
  const uint32_t bytes = udpBytesSent;

  Serial.printf(
      "[link] up_s=%lu loop_hz=%lu ready_pin=%lu ready_i2c=%lu cap_hz=%lu "
      "frame_hz=%lu cap_max_ms=%lu crc_err=%lu rng_err=%lu udp_on=%d "
      "cap_on=%d udp_hz=%lu udp_kbps=%lu udp_dg_max_ms=%lu "
      "udp_frame_max_ms=%lu udp_slow=%lu udp_fail=%lu preempt=%lu "
      "suppress=%lu defer=%lu udp_restarts=%lu "
      "tcp_sess=%lu drops=%lu peer_closed=%lu sent=%lu "
      "gap_max_ms=%lu gap_warn=%lu gap_late=%lu write_max_ms=%lu slow_w=%lu "
      "stalls=%lu partial=%lu mutex_max_ms=%lu mutex_to=%lu tcp_errno=%ld "
      "udp_errno=%ld rssi=%d heap=%lu min_heap=%lu\n",
      static_cast<unsigned long>(now / 1000),
      static_cast<unsigned long>((loopIterations - lastLoops) * 1000UL /
                                 divisor),
      static_cast<unsigned long>(thermalReadyByPin),
      static_cast<unsigned long>(thermalReadyByI2c),
      static_cast<unsigned long>(
          (thermalCaptureAttempts - lastAttempts) * 1000UL / divisor),
      static_cast<unsigned long>((thermalSequence - lastFrames) * 1000UL /
                                 divisor),
      static_cast<unsigned long>(thermalCaptureMaxMs),
      static_cast<unsigned long>(thermalCrcErrors),
      static_cast<unsigned long>(thermalRangeErrors),
      thermalUdpEnabled ? 1 : 0,
      thermalCaptureEnabled ? 1 : 0,
      static_cast<unsigned long>((datagrams - lastDatagrams) * 1000UL /
                                 divisor),
      static_cast<unsigned long>((bytes - lastBytes) * 8UL / divisor),
      static_cast<unsigned long>(udpDatagramMaxMs),
      static_cast<unsigned long>(udpFrameMaxMs),
      static_cast<unsigned long>(udpSlowDatagrams),
      static_cast<unsigned long>(thermalUdpSendFailures),
      static_cast<unsigned long>(thermalFramesPreempted),
      static_cast<unsigned long>(thermalFramesSuppressed),
      static_cast<unsigned long>(thermalFramesDeferred),
      static_cast<unsigned long>(udpSocketRestarts),
      static_cast<unsigned long>(tcpSessions),
      static_cast<unsigned long>(tcpDrops),
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
      static_cast<unsigned long>(tcpMutexTimeouts),
      static_cast<long>(tcpLastErrno),
      static_cast<long>(udpLastErrno),
      static_cast<int>(WiFi.RSSI()),
      static_cast<unsigned long>(ESP.getFreeHeap()),
      static_cast<unsigned long>(ESP.getMinFreeHeap()));

  lastSampleMs = now;
  lastLoops = loopIterations;
  lastAttempts = thermalCaptureAttempts;
  lastFrames = thermalSequence;
  lastDatagrams = datagrams;
  lastBytes = bytes;
}

// Only the peak gauges and diagnostic tallies are cleared. Wire-visible state
// -- telemetrySequence, thermalSequence -- is left alone, because the Pi
// rejects a sequence that moves backwards inside one connection.
void resetDiagnosticCounters() {
  tcpSessions = 0;
  tcpDrops = 0;
  tcpShortSessions = 0;
  tcpPeerClosed = 0;
  tcpWriteStalls = 0;
  tcpPartialWrites = 0;
  tcpMutexTimeouts = 0;
  tcpMutexWaitMaxMs = 0;
  tcpMutexWaitSlow = 0;
  tcpWriteMaxMs = 0;
  tcpSlowWrites = 0;
  telemetryGapMaxMs = 0;
  telemetryGapOverWarn = 0;
  telemetryGapOverDeadline = 0;
  telemetryPacketsSent = 0;
  udpDatagramsSent = 0;
  udpBytesSent = 0;
  udpDatagramMaxMs = 0;
  udpSlowDatagrams = 0;
  udpFrameMaxMs = 0;
  thermalFramesSuppressed = 0;
  thermalFramesDeferred = 0;
  thermalTcpYields = 0;
  udpSocketRestarts = 0;
  tcpLastErrno = 0;
  udpLastErrno = 0;
  thermalCaptureAttempts = 0;
  thermalReadyByPin = 0;
  thermalReadyByI2c = 0;
  thermalCaptureMaxMs = 0;
}

void printDiagnosticHelp() {
  Serial.println(
      "[help] serial commands: u = toggle thermal UDP transmit, "
      "c = toggle thermal capture, s = print [link] now, "
      "l = toggle periodic [link], r = reset diagnostic counters, "
      "h = this help");
  Serial.printf(
      "[help] pi receive deadlines: LCD server settimeout=%lu ms, runtime "
      "gateway=5000 ms; this node warns at gap_ms>=%lu\n",
      static_cast<unsigned long>(PI_PACKET_DEADLINE_MS),
      static_cast<unsigned long>(TELEMETRY_GAP_WARN_MS));
  Serial.println(
      "[help] to prove causation: watch [link] with udp_on=1, press 'u', "
      "watch it again. If gap_max_ms and drops stop growing, the thermal UDP "
      "stream is what closes the TCP connection.");
}

// Non-blocking, so the delay-free runtime contract of loop() still holds.
void handleSerialCommand() {
  while (Serial.available() > 0) {
    switch (Serial.read()) {
      case 'u':
      case 'U':
        thermalUdpEnabled = !thermalUdpEnabled;
        Serial.printf("[cmd] thermal UDP transmit %s\n",
                      thermalUdpEnabled ? "ENABLED" : "DISABLED");
        break;
      case 'c':
      case 'C':
        thermalCaptureEnabled = !thermalCaptureEnabled;
        Serial.printf("[cmd] thermal capture %s\n",
                      thermalCaptureEnabled ? "ENABLED" : "DISABLED");
        break;
      case 'r':
      case 'R':
        resetDiagnosticCounters();
        Serial.println("[cmd] diagnostic counters cleared");
        break;
      case 's':
      case 'S':
        // One-shot, independent of the periodic gate, so 's' still works while
        // the periodic copy is silenced.
        linkDiagnosticsOnce = true;
        break;
      case 'l':
      case 'L':
        linkDiagnosticsEnabled = !linkDiagnosticsEnabled;
        Serial.printf("[cmd] periodic [link] logging %s\n",
                      linkDiagnosticsEnabled ? "ENABLED" : "DISABLED");
        break;
      case 'h':
      case 'H':
      case '?':
        printDiagnosticHelp();
        break;
      default:
        break;  // Ignore newlines and stray bytes from the terminal.
    }
  }
}

void setup() {
  Serial.begin(USB_BAUD);
  setupWait(500);
  Serial.println("\nSafeNest ESP32 sensor node starting");
  initializeBootId();
  Serial.printf("[identity] device=%s boot=%s firmware=%s diag=%s reset=%d\n",
                DEVICE_ID, bootId, NODE_FIRMWARE_VERSION,
                DIAGNOSTIC_BUILD_ID, static_cast<int>(esp_reset_reason()));
  printDiagnosticHelp();

  pinMode(PIN_PIR, INPUT);
  pinMode(PIN_THERMAL_CS, OUTPUT);
  digitalWrite(PIN_THERMAL_CS, HIGH);
  pinMode(PIN_THERMAL_READY, INPUT);
  pinMode(PIN_THERMAL_RESET, OUTPUT);
  digitalWrite(PIN_THERMAL_RESET, HIGH);

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.setClock(100000);
  thermalSpi.begin(PIN_THERMAL_SCLK, PIN_THERMAL_MISO,
                   PIN_THERMAL_MOSI, PIN_THERMAL_CS);

  // setPins() before the library's begin() makes its pin-less Serial.begin()
  // retain GPIO16/17 on both Arduino-ESP32 core 2.x and 3.x.
  mmWaveSerial.setPins(PIN_MMWAVE_RX, PIN_MMWAVE_TX);
  mmWave.begin(&mmWaveSerial, MMWAVE_BAUD, 0);
  Serial.printf(
      "[co2] disabled; UART1 reserved but not initialized (rx=%d tx=%d)\n",
      PIN_CO2_UART_RX, PIN_CO2_UART_TX);

  telemetryQueue = xQueueCreate(1, sizeof(TelemetrySnapshot));
  thermalQueue = xQueueCreate(1, sizeof(ThermalTxFrame));
  networkEvents = xEventGroupCreate();
  networkTxMutex = xSemaphoreCreateMutex();
  if (telemetryQueue == nullptr || thermalQueue == nullptr ||
      networkEvents == nullptr || networkTxMutex == nullptr) {
    Serial.println("[fatal] queue or network synchronization allocation failed");
    while (true) vTaskDelay(portMAX_DELAY);
  }

  initializeThermalCamera();
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // lower latency for the continuous thermal stream
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("[wifi] connecting to %s asynchronously\n", WIFI_SSID);

  // Priority alone cannot preempt datagrams already queued by lwIP, so the
  // per-datagram mutex and TCP critical bit remain required for bounded access.
  xTaskCreatePinnedToCore(telemetryTcpTask, "telemetry-tcp", 8192, nullptr, 2,
                          nullptr, 0);
  xTaskCreatePinnedToCore(thermalUdpTask, "thermal-udp", 8192, nullptr, 1,
                          nullptr, 0);
}

void loop() {
  const uint32_t now = millis();
  ++loopIterations;

  pollMmWave(now);
  pollCo2Uart(now);
  captureThermalIfReady(now);

  if (scheduleDue(now, lastPirPollMs, PIR_PERIOD_MS)) {
    pirMotion = digitalRead(PIN_PIR) == HIGH;
  }

  publishTelemetrySnapshot(now);
  handleSerialCommand();
  logLinkDiagnostics(now);
  logHealth(now);

  // Cooperative yield only; there is intentionally no delay() in runtime.
  taskYIELD();
}
