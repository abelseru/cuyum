#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include "HT_SSD1306Wire.h"
#include "config.h"

/*
  Cuyum ESP32 display node
  Board: Heltec WiFi LoRa 32 V3

  Code and technical comments are in English.
  Text shown on the OLED is in Spanish.

  Main functions:
  - Connect to Wi-Fi.
  - Read the Cuyum /lite endpoint.
  - Rotate general and zone screens.
  - Show a fixed ATTENTION screen during a confirmed notice.
  - Drive an active buzzer module on GPIO 4.
  - Make the integrated LED follow the buzzer pattern.
*/

// -----------------------------------------------------------------------------
// Hardware
// -----------------------------------------------------------------------------

const int LED_PIN = 35;
const int BUZZER_PIN = 4;

// The integrated LED on this board is active LOW.
const int LED_ON = LOW;
const int LED_OFF = HIGH;

// Default polarity for a common active buzzer module.
// Reverse these two values if the purchased module works in the opposite way.
const int BUZZER_ON = HIGH;
const int BUZZER_OFF = LOW;

SSD1306Wire oled(
  0x3c,
  500000,
  SDA_OLED,
  SCL_OLED,
  GEOMETRY_128_64,
  RST_OLED
);

// -----------------------------------------------------------------------------
// Timing
// -----------------------------------------------------------------------------

const unsigned long POLL_INTERVAL_MS = 3000;
const unsigned long SCREEN_INTERVAL_MS = 2500;

const unsigned long BEEP_ON_MS = 180;
const unsigned long BEEP_OFF_MS = 100;
const int NOTICE_BEEP_COUNT = 5;

unsigned long lastPollTime = 0;
unsigned long lastScreenTime = 0;

// -----------------------------------------------------------------------------
// Data model
// -----------------------------------------------------------------------------

const int MAX_ZONES = 10;
const int ZONES_PER_SCREEN = 5;

struct ZoneData {
  String id;
  String name;
  int activeSensors;
  int confirmingSensors;
};

struct CuyumStatus {
  bool valid;

  String network;
  String level;
  String message;

  int activeSensors;
  int calibratedSensors;
  int activeZones;

  bool sound;

  bool attentionActive;
  String attentionDirection;
  int attentionConfirmingSensors;

  int zoneCount;
  ZoneData zones[MAX_ZONES];
};

CuyumStatus statusData;

// -----------------------------------------------------------------------------
// Buzzer and LED pattern state
// -----------------------------------------------------------------------------

bool patternRunning = false;
bool patternOutputOn = false;
int completedBeeps = 0;
unsigned long patternPhaseTime = 0;

// This latch prevents the five-beep pattern from repeating on every poll.
bool soundEpisodeLatched = false;

// -----------------------------------------------------------------------------
// Screen rotation state
// -----------------------------------------------------------------------------

int currentScreen = 0;

// -----------------------------------------------------------------------------
// Basic text helpers
// -----------------------------------------------------------------------------

String shorten(String text, int maximumLength) {
  text.trim();

  if ((int)text.length() <= maximumLength) {
    return text;
  }

  return text.substring(0, maximumLength);
}

String lowerCase(String text) {
  text.toLowerCase();
  return text;
}

String directionInSpanish(String value) {
  String original = value;
  String direction = value;

  direction.trim();
  direction.toUpperCase();

  if (direction == "LOCAL" || direction == "CELL_00") return "Local";

  if (direction == "N" || direction == "NORTH") return "Norte";
  if (direction == "NE" || direction == "NORTHEAST") return "Noreste";
  if (direction == "E" || direction == "EAST") return "Este";
  if (direction == "SE" || direction == "SOUTHEAST") return "Sudeste";
  if (direction == "S" || direction == "SOUTH") return "Sur";

  if (
    direction == "SW" ||
    direction == "SO" ||
    direction == "SOUTHWEST"
  ) {
    return "Suroeste";
  }

  if (
    direction == "W" ||
    direction == "O" ||
    direction == "WEST"
  ) {
    return "Oeste";
  }

  if (
    direction == "NW" ||
    direction == "NO" ||
    direction == "NORTHWEST"
  ) {
    return "Noroeste";
  }

  if (direction.length() == 0) {
    return "Zona";
  }

  return original;
}

String networkInSpanish(String value) {
  String text = lowerCase(value);

  if (
    text.indexOf("complete") >= 0 ||
    text.indexOf("full") >= 0
  ) {
    return "Red completa";
  }

  if (text.indexOf("partial") >= 0) {
    return "Red parcial";
  }

  if (
    text.indexOf("limited") >= 0 ||
    text.indexOf("minimal") >= 0
  ) {
    return "Red limitada";
  }

  if (
    text.indexOf("offline") >= 0 ||
    text.indexOf("no data") >= 0
  ) {
    return "Red sin datos";
  }

  return "Red Cuyum";
}

String levelInSpanish(String level, String message) {
  String text = lowerCase(level + " " + message);

  if (
    text.indexOf("attention") >= 0 ||
    text.indexOf("anticip") >= 0
  ) {
    return "Atencion";
  }

  if (
    text.indexOf("watch") >= 0 ||
    text.indexOf("observ") >= 0
  ) {
    return "Observando";
  }

  if (text.indexOf("normal") >= 0) {
    return "Estado normal";
  }

  if (
    text.indexOf("offline") >= 0 ||
    text.indexOf("no data") >= 0
  ) {
    return "Sin datos";
  }

  return "Sistema activo";
}

// -----------------------------------------------------------------------------
// OLED helpers
// -----------------------------------------------------------------------------

void drawLines(String lines[], int lineCount) {
  oled.clear();
  oled.setTextAlignment(TEXT_ALIGN_LEFT);
  oled.setFont(ArialMT_Plain_10);

  int visibleLines = lineCount;

  if (visibleLines > 6) {
    visibleLines = 6;
  }

  for (int i = 0; i < visibleLines; i++) {
    oled.drawString(0, i * 10, shorten(lines[i], 22));
  }

  oled.display();
}

void startOled() {
  pinMode(Vext, OUTPUT);
  digitalWrite(Vext, LOW);
  delay(100);

  oled.init();

  String lines[6] = {
    "Cuyum",
    "Iniciando",
    "Prueba de salida",
    "",
    "",
    ""
  };

  drawLines(lines, 6);
}

void showConnectionScreen() {
  String lines[6] = {
    "Cuyum",
    "Conectando WiFi",
    String(WIFI_SSID),
    "Espere...",
    "",
    ""
  };

  drawLines(lines, 6);
}

void showWaitingScreen() {
  String lines[6] = {
    "Cuyum",
    "WiFi conectado",
    WiFi.localIP().toString(),
    "Esperando datos",
    "",
    ""
  };

  drawLines(lines, 6);
}

void showErrorScreen(String firstLine, String secondLine) {
  String lines[6] = {
    "Cuyum",
    firstLine,
    secondLine,
    "Revise conexion",
    "y servidor",
    ""
  };

  drawLines(lines, 6);
}

void showGeneralScreen() {
  String lastLine = "Sin avisos";
  String translatedLevel = levelInSpanish(statusData.level, statusData.message);

  if (translatedLevel == "Observando") {
    lastLine = "Senal observada";
  }

  String lines[6] = {
    "Cuyum activo",
    networkInSpanish(statusData.network),
    translatedLevel,
    String("Zonas: ") + statusData.activeZones,
    String("Sensores: ") + statusData.activeSensors,
    lastLine
  };

  drawLines(lines, 6);
}

void showZonesScreen(int page) {
  String lines[6] = {
    "Sensores por zona",
    "",
    "",
    "",
    "",
    ""
  };

  int firstZone = page * ZONES_PER_SCREEN;

  for (int row = 0; row < ZONES_PER_SCREEN; row++) {
    int zoneIndex = firstZone + row;

    if (zoneIndex >= statusData.zoneCount) {
      break;
    }

    ZoneData zone = statusData.zones[zoneIndex];

    lines[row + 1] =
      shorten(zone.name, 13) +
      ": " +
      String(zone.activeSensors);
  }

  drawLines(lines, 6);
}

void showAttentionScreen() {
  String sensorWord = "sensores";

  if (statusData.attentionConfirmingSensors == 1) {
    sensorWord = "sensor";
  }

  String lines[6] = {
    "ATENCION",
    "Direccion:",
    directionInSpanish(statusData.attentionDirection),
    "Coinciden:",
    String(statusData.attentionConfirmingSensors) + " " + sensorWord,
    "Aviso experimental"
  };

  drawLines(lines, 6);
}

int zonePageCount() {
  if (statusData.zoneCount == 0) {
    return 1;
  }

  return (statusData.zoneCount + ZONES_PER_SCREEN - 1) / ZONES_PER_SCREEN;
}

int normalScreenCount() {
  return 1 + zonePageCount();
}

void updateScreen(bool forceUpdate) {
  if (statusData.attentionActive) {
    showAttentionScreen();
    return;
  }

  if (!statusData.valid) {
    return;
  }

  unsigned long now = millis();

  if (
    !forceUpdate &&
    now - lastScreenTime < SCREEN_INTERVAL_MS
  ) {
    return;
  }

  lastScreenTime = now;

  if (forceUpdate) {
    currentScreen = 0;
  } else {
    currentScreen++;

    if (currentScreen >= normalScreenCount()) {
      currentScreen = 0;
    }
  }

  if (currentScreen == 0) {
    showGeneralScreen();
  } else {
    showZonesScreen(currentScreen - 1);
  }
}

// -----------------------------------------------------------------------------
// Buzzer and LED
// -----------------------------------------------------------------------------

void writeNoticeOutputs(bool turnOn) {
  if (turnOn) {
    digitalWrite(LED_PIN, LED_ON);
    digitalWrite(BUZZER_PIN, BUZZER_ON);
  } else {
    digitalWrite(LED_PIN, LED_OFF);
    digitalWrite(BUZZER_PIN, BUZZER_OFF);
  }
}

void prepareNoticeOutputs() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  writeNoticeOutputs(false);
}

void runStartupTest() {
  Serial.println("STARTUP_OUTPUT_TEST");

  writeNoticeOutputs(true);
  delay(BEEP_ON_MS);
  writeNoticeOutputs(false);
}

void startNoticePattern() {
  if (patternRunning) {
    return;
  }

  patternRunning = true;
  patternOutputOn = true;
  completedBeeps = 0;
  patternPhaseTime = millis();

  writeNoticeOutputs(true);

  Serial.println("NOTICE_PATTERN_START");
}

void updateNoticePattern() {
  if (!patternRunning) {
    return;
  }

  unsigned long now = millis();

  if (
    patternOutputOn &&
    now - patternPhaseTime >= BEEP_ON_MS
  ) {
    writeNoticeOutputs(false);

    patternOutputOn = false;
    completedBeeps++;
    patternPhaseTime = now;

    if (completedBeeps >= NOTICE_BEEP_COUNT) {
      patternRunning = false;
      Serial.println("NOTICE_PATTERN_END");
    }

    return;
  }

  if (
    !patternOutputOn &&
    now - patternPhaseTime >= BEEP_OFF_MS
  ) {
    writeNoticeOutputs(true);

    patternOutputOn = true;
    patternPhaseTime = now;
  }
}

void updateSoundEpisode() {
  if (statusData.sound) {
    if (!soundEpisodeLatched) {
      soundEpisodeLatched = true;
      startNoticePattern();
    }

    return;
  }

  // The system becomes ready for a new episode only after sound returns false.
  soundEpisodeLatched = false;
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char command = Serial.read();

    if (command == 't' || command == 'T') {
      Serial.println("MANUAL_NOTICE_PATTERN_TEST");
      startNoticePattern();
    }
  }
}

// -----------------------------------------------------------------------------
// Wi-Fi
// -----------------------------------------------------------------------------

void connectWiFi() {
  showConnectionScreen();

  Serial.println();
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;

  while (
    WiFi.status() != WL_CONNECTED &&
    attempts < 30
  ) {
    updateNoticePattern();
    delay(500);

    Serial.print(".");
    attempts++;
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Wi-Fi connected.");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());

    showWaitingScreen();
  } else {
    Serial.println("Wi-Fi connection failed.");
    showErrorScreen("Error de WiFi", "No conecta");
  }
}

// -----------------------------------------------------------------------------
// JSON reading
// -----------------------------------------------------------------------------

void clearZones() {
  statusData.zoneCount = 0;
}

void readZones(JsonVariant root) {
  clearZones();

  JsonArray cells;

  if (root["display_cells"].is<JsonArray>()) {
    cells = root["display_cells"].as<JsonArray>();
  } else if (root["display"]["cells"].is<JsonArray>()) {
    cells = root["display"]["cells"].as<JsonArray>();
  } else {
    return;
  }

  for (JsonObject cell : cells) {
    if (statusData.zoneCount >= MAX_ZONES) {
      break;
    }

    String cellId = String(cell["cell_id"] | "");
    String role = String(cell["role"] | "");

    // Regional observers are useful to Cuyum but are not a direction screen.
    if (
      cellId == "regional_observers" ||
      role == "regional_observer"
    ) {
      continue;
    }

    String direction = String(cell["direction_label"] | "");
    String shortLabel = String(cell["short_label"] | "");

    if (direction.length() == 0) {
      direction = shortLabel;
    }

    int index = statusData.zoneCount;

    statusData.zones[index].id = cellId;
    statusData.zones[index].name = directionInSpanish(direction);
    statusData.zones[index].activeSensors = cell["sensors_active"] | 0;
    statusData.zones[index].confirmingSensors = cell["confirming"] | 0;

    statusData.zoneCount++;
  }
}

bool readStatusJson(String payload) {
  DynamicJsonDocument document(12288);

  DeserializationError error = deserializeJson(document, payload);

  if (error) {
    Serial.print("JSON parse error: ");
    Serial.println(error.c_str());
    return false;
  }

  JsonVariant root = document.as<JsonVariant>();

  statusData.network = String(root["display"]["network"] | "");
  if (statusData.network.length() == 0) {
    statusData.network = String(root["network_quality"] | "unknown");
  }

  statusData.level = String(root["display"]["status"] | "");
  if (statusData.level.length() == 0) {
    statusData.level = String(root["level"] | "normal");
  }

  statusData.message = String(root["display"]["message"] | "");
  if (statusData.message.length() == 0) {
    statusData.message = String(root["message"] | "");
  }

  statusData.activeSensors = root["active_sensors"] | 0;
  statusData.calibratedSensors = root["calibrated_sensors"] | 0;
  statusData.activeZones = root["cells_active"] | 0;

  statusData.sound = root["sound"] | false;

  statusData.attentionActive =
    root["attention"]["active"] | statusData.sound;

  statusData.attentionDirection =
    String(root["attention"]["direction_label"] | "");

  if (statusData.attentionDirection.length() == 0) {
    statusData.attentionDirection =
      String(root["attention"]["direction"] | "Zona");
  }

  statusData.attentionConfirmingSensors =
    root["attention"]["confirming_sensors"] | 0;

  if (statusData.attentionConfirmingSensors == 0) {
    statusData.attentionConfirmingSensors =
      root["total_confirming_stations"] | 0;
  }

  readZones(root);

  statusData.valid = true;

  updateSoundEpisode();

  return true;
}

// -----------------------------------------------------------------------------
// HTTP request
// -----------------------------------------------------------------------------

void pollCuyumStatus() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Wi-Fi disconnected. Trying again.");
    connectWiFi();
    return;
  }

  HTTPClient http;

  Serial.print("Polling: ");
  Serial.println(STATUS_URL);

  http.begin(STATUS_URL);

  int responseCode = http.GET();

  if (responseCode != HTTP_CODE_OK) {
    Serial.print("HTTP response code: ");
    Serial.println(responseCode);

    showErrorScreen("Error HTTP", String(responseCode));
    http.end();
    return;
  }

  String payload = http.getString();
  http.end();

  payload.trim();

  if (!payload.startsWith("{")) {
    Serial.println("Invalid non-JSON response.");
    showErrorScreen("Respuesta", "no valida");
    return;
  }

  bool firstValidStatus = !statusData.valid;

  if (!readStatusJson(payload)) {
    showErrorScreen("Error de JSON", "No se pudo leer");
    return;
  }

  Serial.print("Level: ");
  Serial.println(statusData.level);

  Serial.print("Active sensors: ");
  Serial.println(statusData.activeSensors);

  Serial.print("Attention: ");
  Serial.println(statusData.attentionActive ? "true" : "false");

  Serial.print("Direction: ");
  Serial.println(statusData.attentionDirection);

  Serial.print("Confirming sensors: ");
  Serial.println(statusData.attentionConfirmingSensors);

  if (
    firstValidStatus ||
    statusData.attentionActive
  ) {
    updateScreen(true);
  }
}

// -----------------------------------------------------------------------------
// Arduino setup and loop
// -----------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(800);

  statusData.valid = false;
  statusData.zoneCount = 0;

  prepareNoticeOutputs();
  startOled();
  runStartupTest();
  connectWiFi();

  Serial.println("Cuyum ESP32 node started.");
  Serial.println("Serial command: T = manual five-beep test.");

  lastPollTime = millis() - POLL_INTERVAL_MS;
  lastScreenTime = millis();
}

void loop() {
  updateNoticePattern();
  readSerialCommands();

  unsigned long now = millis();

  if (now - lastPollTime >= POLL_INTERVAL_MS) {
    lastPollTime = now;
    pollCuyumStatus();
  }

  updateScreen(false);
  updateNoticePattern();
}
