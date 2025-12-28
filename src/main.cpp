/*
 * Copyright 2025 Arduino PT2D Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @file main.cpp
 * @brief 橋接固件：PC <...> 協議 與 二軸開發板總線 #...! 指令之間的轉換/透傳
 * @date 2025-12-24
 *
 * - 解析 PC 端以 <...> 形式的命令（最小集合）
 * - 支援直接透傳以 # 開頭的總線指令（#...!）
 * - 分離 PC 調試串口與總線串口（UNO/Nano 使用 SoftwareSerial；Mega 使用 Serial1）
 */

#include <Arduino.h>
#include <avr/wdt.h>  // 看門狗定時器
#include "config.h"

#if !defined(__AVR_ATmega2560__)
#include <SoftwareSerial.h>
SoftwareSerial BUS_SERIAL(SERVO_TX_PIN, SERVO_RX_PIN);
#else
#define BUS_SERIAL Serial1
#endif

// 固定大小緩衝區（避免 String 類的 heap 碎片化）
static char pcBuf[128];
static uint8_t pcBufLen = 0;
static char busBuf[64];
static uint8_t busBufLen = 0;

enum BusCmdType { BUS_NONE = 0, BUS_READ_ANGLE, BUS_READ_VOLTEMP };
static BusCmdType lastBusCmd = BUS_NONE;
static int lastBusId = -1;

// 動態舵機 ID（執行時可修改）
static int panServoId = DEFAULT_PAN_SERVO_ID;
static int tiltServoId = DEFAULT_TILT_SERVO_ID;
static boolean servoIdDetected = false;

// 移動參數（全局）
static int moveSpeed = DEFAULT_SPEED;
static int moveTime = 1000;  // 預設時間（ms）

// 聚合狀態：POS 與 STATUS（雙軸）
enum AggType { AGG_NONE = 0, AGG_POS_BOTH, AGG_STATUS_BOTH };
static AggType aggType = AGG_NONE;
static int aggPhase = 0;
static int aggPanAngle = -1;
static int aggTiltAngle = -1;
static int aggPanVolt = -1;
static int aggPanTemp = -1;
static int aggTiltVolt = -1;
static int aggTiltTemp = -1;
static unsigned long aggTimeout = 0;  // 聚合命令超時保護（毫秒）

// 超時設定（毫秒）
#define AGG_CMD_TIMEOUT 2000  // 聚合命令最大等待時間

static void setup_led() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH); // 熄滅
}

static void setup_beep() {
  pinMode(BEEP_PIN, OUTPUT);
  digitalWrite(BEEP_PIN, HIGH); // 關閉
}

static void setup_laser() {
  pinMode(LASER_PIN, OUTPUT);
  digitalWrite(LASER_PIN, LOW); // 雷射關閉
}

static void setup_uart() {
  Serial.begin(SERIAL_BAUDRATE);
}

static void setup_bus() {
  BUS_SERIAL.begin(SERVO_BAUDRATE);
}

// ============================================
// 輔助函數：參數驗證與字串處理
// ============================================

// 驗證舵機 ID 是否有效（1-254）
static bool isValidServoId(int id) {
  return (id >= 1 && id <= 254);
}

// 驗證角度是否在範圍內
static bool isValidAngle(int angle, int maxAngle) {
  return (angle >= 0 && angle <= maxAngle);
}

// 安全的整數解析（避免 toInt() 的未定義行為）
static bool parseIntParam(const char* str, int& result) {
  if (!str || *str == '\0') return false;
  char* endptr;
  long val = strtol(str, &endptr, 10);
  if (*endptr != '\0' && *endptr != ',' && *endptr != ' ') return false;
  result = (int)val;
  return true;
}

// 解析逗號分隔的兩個整數
static bool parseTwoInts(const char* params, int& val1, int& val2) {
  const char* comma = strchr(params, ',');
  if (!comma) return false;

  char buf1[16], buf2[16];
  int len1 = comma - params;
  if (len1 >= 16) return false;
  strncpy(buf1, params, len1);
  buf1[len1] = '\0';

  strncpy(buf2, comma + 1, 15);
  buf2[15] = '\0';

  return parseIntParam(buf1, val1) && parseIntParam(buf2, val2);
}

// 字串轉大寫（in-place）
static void toUpperCase(char* str) {
  while (*str) {
    if (*str >= 'a' && *str <= 'z') *str -= 32;
    str++;
  }
}

// 清空緩衝區
static void clearBuf(char* buf, uint8_t& len) {
  buf[0] = '\0';
  len = 0;
}

// 重置聚合狀態
static void resetAggState() {
  aggType = AGG_NONE;
  aggPhase = 0;
  aggPanAngle = aggTiltAngle = -1;
  aggPanVolt = aggTiltVolt = -1;
  aggPanTemp = aggTiltTemp = -1;
  aggTimeout = 0;
  clearBuf(busBuf, busBufLen);
}

// JSON 錯誤回應
static void sendError(const char* msg) {
  Serial.print("{\"status\":\"error\",\"message\":\"");
  Serial.print(msg);
  Serial.println("\"}");
}

static void sendOk() {
  Serial.println("{\"status\":\"ok\",\"message\":\"OK\"}");
}

// 自動掃描舵機 ID
static void autoDetectServoId() {
  if (!AUTO_DETECT_SERVO_ID) {
    servoIdDetected = true;
    return;
  }

  Serial.println("{\"status\":\"info\",\"message\":\"啟動舵機ID自動掃描\"}");

  // 嘗試掃描 Pan 舵機
  for (int id = 1; id <= 5; id++) {
    char buf[16];
    snprintf(buf, sizeof(buf), "#%03dPID!", id);
    sendBus(buf);
    delay(SERVO_DETECT_INTERVAL);

    // 檢查回應
    unsigned long timeout = millis() + SERVO_DETECT_TIMEOUT;
    while (millis() < timeout && BUS_SERIAL.available()) {
      char c = (char)BUS_SERIAL.read();
      if (c == '!') {
        panServoId = id;
        Serial.print("{\"status\":\"info\",\"message\":\"Pan舵機ID\",\"id\":");
        Serial.print(panServoId);
        Serial.println("}");
        break;
      }
    }
  }

  delay(100);

  // 嘗試掃描 Tilt 舵機
  for (int id = 1; id <= 5; id++) {
    if (id == panServoId) continue;  // 跳過已使用的ID

    char buf[16];
    snprintf(buf, sizeof(buf), "#%03dPID!", id);
    sendBus(buf);
    delay(SERVO_DETECT_INTERVAL);

    // 檢查回應
    unsigned long timeout = millis() + SERVO_DETECT_TIMEOUT;
    while (millis() < timeout && BUS_SERIAL.available()) {
      char c = (char)BUS_SERIAL.read();
      if (c == '!') {
        tiltServoId = id;
        Serial.print("{\"status\":\"info\",\"message\":\"Tilt舵機ID\",\"id\":");
        Serial.print(tiltServoId);
        Serial.println("}");
        break;
      }
    }
  }

  // 清空緩衝區
  while (BUS_SERIAL.available()) {
    BUS_SERIAL.read();
  }

  servoIdDetected = true;
  Serial.println("{\"status\":\"info\",\"message\":\"舵機掃描完成\"}");
}

static void beep_short3() {
  for (int i = 0; i < 3; i++) {
    digitalWrite(BEEP_PIN, LOW);
    delay(100);
    digitalWrite(BEEP_PIN, HIGH);
    delay(100);
  }
}

static void forwardBusResponse() {
  // 將總線回覆透傳到 PC
  while (BUS_SERIAL.available()) {
    char c = (char)BUS_SERIAL.read();
    Serial.write(c);
  }
}

static void sendBus(const char* cmd) {
  // 將 #...! 指令送往總線
  BUS_SERIAL.print(cmd);
  BUS_SERIAL.flush();
}

// 角度轉位置函數
static uint16_t angleToPosition(int angle) {
  if (angle < 0) angle = 0;
  if (angle > SERVO_MAX_ANGLE) angle = SERVO_MAX_ANGLE;
  return (uint16_t)map(angle, 0, SERVO_MAX_ANGLE, 0, 1000);
}

// ============================================
// 命令處理函數
// ============================================

// 處理 LED 命令
static void handleLed(const char* params) {
  char paramsCopy[16];
  strncpy(paramsCopy, params, 15);
  paramsCopy[15] = '\0';
  toUpperCase(paramsCopy);

  if (strcmp(paramsCopy, "ON") == 0) {
    digitalWrite(LED_PIN, LOW);
  } else {
    digitalWrite(LED_PIN, HIGH);
  }
  Serial.println("{\"status\":\"ok\",\"message\":\"LED\"}");
}

// 處理 BEEP 命令
static void handleBeep() {
  beep_short3();
  Serial.println("{\"status\":\"ok\",\"message\":\"BEEP\"}");
}

// 處理 LASER 命令
static void handleLaser(const char* params) {
  char paramsCopy[16];
  strncpy(paramsCopy, params, 15);
  paramsCopy[15] = '\0';
  toUpperCase(paramsCopy);

  if (strcmp(paramsCopy, "ON") == 0) {
    digitalWrite(LASER_PIN, HIGH);  // 雷射開啟
    Serial.println("{\"status\":\"ok\",\"message\":\"LASER_ON\"}");
  } else if (strcmp(paramsCopy, "OFF") == 0) {
    digitalWrite(LASER_PIN, LOW);   // 雷射關閉
    Serial.println("{\"status\":\"ok\",\"message\":\"LASER_OFF\"}");
  } else {
    sendError("Invalid parameter (ON/OFF)");
  }
}

// 處理 SPEED 命令
static void handleSpeed(const char* params) {
  int val;
  if (!parseIntParam(params, val)) {
    sendError("Invalid parameter");
    return;
  }
  if (val < 1) val = 1;
  if (val > 100) val = 100;
  moveSpeed = val;
  moveTime = map(moveSpeed, 1, 100, 5000, 100);
  sendOk();
}

// 處理 SETID 命令
static void handleSetId(const char* params) {
  int newPanId, newTiltId;
  if (!parseTwoInts(params, newPanId, newTiltId)) {
    sendError("Invalid parameter");
    return;
  }
  if (!isValidServoId(newPanId) || !isValidServoId(newTiltId)) {
    sendError("Invalid servo ID");
    return;
  }
  panServoId = newPanId;
  tiltServoId = newTiltId;
  Serial.print("{\"status\":\"ok\",\"pan_id\":");
  Serial.print(panServoId);
  Serial.print(",\"tilt_id\":");
  Serial.print(tiltServoId);
  Serial.println("}");
}

// 處理 MOVE/MOVETO 命令
static void handleMove(const char* params) {
  int panAngle, tiltAngle;
  if (!parseTwoInts(params, panAngle, tiltAngle)) {
    sendError("Invalid parameter");
    return;
  }

  uint16_t panPos = angleToPosition(panAngle);
  uint16_t tiltPos = angleToPosition(tiltAngle);
  char buf[32];
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, panPos, moveTime);
  sendBus(buf);
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, tiltPos, moveTime);
  sendBus(buf);
  sendOk();
}

// 處理 STOP 命令
static void handleStop() {
  char buf[24];
  snprintf(buf, sizeof(buf), "#%03dPDST!", panServoId);
  sendBus(buf);
  snprintf(buf, sizeof(buf), "#%03dPDST!", tiltServoId);
  sendBus(buf);
  sendOk();
}

// 處理 HOME 命令
static void handleHome() {
  uint16_t panPos = angleToPosition(PAN_INIT_ANGLE);
  uint16_t tiltPos = angleToPosition(TILT_INIT_ANGLE);
  char buf[32];
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, panPos, moveTime);
  sendBus(buf);
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, tiltPos, moveTime);
  sendBus(buf);
  sendOk();
}

// 處理 POS/GETPOS 命令（啟動聚合讀取雙軸角度）
static void handleGetPos() {
  aggType = AGG_POS_BOTH;
  aggPhase = 0;
  aggPanAngle = aggTiltAngle = -1;
  aggTimeout = millis() + AGG_CMD_TIMEOUT;
  clearBuf(busBuf, busBufLen);

  char buf[24];
  snprintf(buf, sizeof(buf), "#%03dPRAD!", panServoId);
  sendBus(buf);
}

// 處理 STATUS/INFO 命令（啟動聚合讀取雙軸完整狀態）
static void handleStatus() {
  aggType = AGG_STATUS_BOTH;
  aggPhase = 0;
  aggPanAngle = aggTiltAngle = -1;
  aggPanVolt = aggTiltVolt = -1;
  aggPanTemp = aggTiltTemp = -1;
  aggTimeout = millis() + AGG_CMD_TIMEOUT;
  clearBuf(busBuf, busBufLen);

  char buf[24];
  snprintf(buf, sizeof(buf), "#%03dPRAD!", panServoId);
  sendBus(buf);
}

// 處理 READANGLE 命令
static void handleReadAngle(const char* params) {
  int id;
  if (!parseIntParam(params, id) || !isValidServoId(id)) {
    sendError("Invalid parameter");
    return;
  }

  char buf[24];
  snprintf(buf, sizeof(buf), "#%03dPRAD!", id);
  lastBusCmd = BUS_READ_ANGLE;
  lastBusId = id;
  clearBuf(busBuf, busBufLen);
  sendBus(buf);
}

// 處理 READVOLTEMP 命令
static void handleReadVolTemp(const char* params) {
  int id;
  if (!parseIntParam(params, id) || !isValidServoId(id)) {
    sendError("Invalid parameter");
    return;
  }

  char buf[24];
  snprintf(buf, sizeof(buf), "#%03dPRTV!", id);
  lastBusCmd = BUS_READ_VOLTEMP;
  lastBusId = id;
  clearBuf(busBuf, busBufLen);
  sendBus(buf);
}

// 處理 MOVER/MOVEBY 命令（相對移動）
static void handleMoveBy(const char* params) {
  int panDelta, tiltDelta;
  if (!parseTwoInts(params, panDelta, tiltDelta)) {
    sendError("Invalid parameter");
    return;
  }

  // 讀取當前位置後加上偏移
  int currentPan = 135;  // 預設中心
  int currentTilt = 90;
  int newPan = currentPan + panDelta;
  int newTilt = currentTilt + tiltDelta;

  // 限制在範圍內
  if (newPan < 0) newPan = 0;
  if (newPan > SERVO_MAX_ANGLE) newPan = SERVO_MAX_ANGLE;
  if (newTilt < 0) newTilt = 0;
  if (newTilt > 180) newTilt = 180;

  uint16_t panPos = angleToPosition(newPan);
  uint16_t tiltPos = angleToPosition(newTilt);
  char buf[32];
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, panPos, moveTime);
  sendBus(buf);
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, tiltPos, moveTime);
  sendBus(buf);
  sendOk();
}

// 處理 CAL/CALIBRATE 命令
static void handleCalibrate() {
  char buf[32];

  // 移動到中心位置 (135°, 90°)
  uint16_t centerPan = angleToPosition(135);
  uint16_t centerTilt = angleToPosition(90);
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, centerPan, 2000);
  sendBus(buf);
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, centerTilt, 2000);
  sendBus(buf);
  delay(2500);

  // Pan 最小 (0°)
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, 0, 2000);
  sendBus(buf);
  delay(2500);

  // Pan 最大 (270°)
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, 1000, 2000);
  sendBus(buf);
  delay(2500);

  // Tilt 最小 (0°)
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, 0, 2000);
  sendBus(buf);
  delay(2500);

  // Tilt 最大 (180°)
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, 1000, 2000);
  sendBus(buf);
  delay(2500);

  // 回到初始位置
  uint16_t panPos = angleToPosition(PAN_INIT_ANGLE);
  uint16_t tiltPos = angleToPosition(TILT_INIT_ANGLE);
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, panPos, 2000);
  sendBus(buf);
  snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, tiltPos, 2000);
  sendBus(buf);

  sendOk();
}

// ============================================
// 主命令處理函數（重構為簡潔的命令分發器）
// ============================================

static void handlePcLine(const char* line) {
  // 1) 直接透傳 #...! 指令到總線
  if (line[0] == '#') {
    sendBus(line);
    return;
  }

  // 2) 解析 <CMD:PARAMS> 格式
  if (line[0] != '<' || line[strlen(line)-1] != '>') {
    return;  // 格式錯誤，靜默忽略
  }

  // 提取內容（去除 < 和 >）
  char inner[120];
  strncpy(inner, line + 1, sizeof(inner) - 1);
  inner[sizeof(inner) - 1] = '\0';
  inner[strlen(inner) - 1] = '\0';  // 移除 >

  // 分離命令類型和參數
  char* colon = strchr(inner, ':');
  char cmdType[20];
  const char* params = "";

  if (colon) {
    int cmdLen = colon - inner;
    if (cmdLen >= sizeof(cmdType)) cmdLen = sizeof(cmdType) - 1;
    strncpy(cmdType, inner, cmdLen);
    cmdType[cmdLen] = '\0';
    params = colon + 1;
  } else {
    strncpy(cmdType, inner, sizeof(cmdType) - 1);
    cmdType[sizeof(cmdType) - 1] = '\0';
  }

  toUpperCase(cmdType);

  // 3) 命令分發（使用提取的函數）
  if (strcmp(cmdType, "RAW") == 0) {
    lastBusCmd = BUS_NONE;
    lastBusId = -1;
    sendBus(params);
  }
  else if (strcmp(cmdType, "LED") == 0) handleLed(params);
  else if (strcmp(cmdType, "BEEP") == 0) handleBeep();
  else if (strcmp(cmdType, "LASER") == 0) handleLaser(params);
  else if (strcmp(cmdType, "SPEED") == 0) handleSpeed(params);
  else if (strcmp(cmdType, "SETID") == 0) handleSetId(params);
  else if (strcmp(cmdType, "MOVE") == 0 || strcmp(cmdType, "MOVETO") == 0) handleMove(params);
  else if (strcmp(cmdType, "STOP") == 0) handleStop();
  else if (strcmp(cmdType, "HOME") == 0) handleHome();
  else if (strcmp(cmdType, "POS") == 0 || strcmp(cmdType, "GETPOS") == 0) handleGetPos();
  else if (strcmp(cmdType, "STATUS") == 0 || strcmp(cmdType, "INFO") == 0) handleStatus();
  else if (strcmp(cmdType, "READANGLE") == 0) handleReadAngle(params);
  else if (strcmp(cmdType, "READVOLTEMP") == 0) handleReadVolTemp(params);
  else if (strcmp(cmdType, "MOVER") == 0 || strcmp(cmdType, "MOVEBY") == 0) handleMoveBy(params);
  else if (strcmp(cmdType, "READ") == 0 || strcmp(cmdType, "READPOS") == 0) handleGetPos();
  else if (strcmp(cmdType, "TEMP") == 0 || strcmp(cmdType, "TEMPERATURE") == 0) {
    // 復用 STATUS 流程但只輸出溫度
    aggType = AGG_STATUS_BOTH;
    aggPhase = 0;
    aggPanAngle = aggTiltAngle = -1;
    aggPanVolt = aggTiltVolt = -1;
    aggPanTemp = aggTiltTemp = -1;
    aggTimeout = millis() + AGG_CMD_TIMEOUT;
    clearBuf(busBuf, busBufLen);
    char buf[24];
    snprintf(buf, sizeof(buf), "#%03dPRTV!", panServoId);
    sendBus(buf);
  }
  else if (strcmp(cmdType, "VOLT") == 0 || strcmp(cmdType, "VOLTAGE") == 0) {
    // 復用 STATUS 流程但只輸出電壓
    aggType = AGG_STATUS_BOTH;
    aggPhase = 0;
    aggPanAngle = aggTiltAngle = -1;
    aggPanVolt = aggTiltVolt = -1;
    aggPanTemp = aggTiltTemp = -1;
    aggTimeout = millis() + AGG_CMD_TIMEOUT;
    clearBuf(busBuf, busBufLen);
    char buf[24];
    snprintf(buf, sizeof(buf), "#%03dPRTV!", panServoId);
    sendBus(buf);
  }
  else if (strcmp(cmdType, "CAL") == 0 || strcmp(cmdType, "CALIBRATE") == 0) handleCalibrate();
  else {
    sendError("Unknown command");
  }
}

void setup() {
  // 禁用看門狗（防止啟動時重置）
  wdt_disable();

  setup_led();
  setup_beep();
  setup_laser();  // 初始化雷射控制
  setup_uart();
  setup_bus();

  Serial.println(F("{\"status\":\"info\",\"message\":\"PT2D Bridge Firmware v2.3.0\"}"));
  Serial.println(F("{\"status\":\"info\",\"message\":\"PC <...> / BUS #...!\"}"));
  beep_short3();

  // 啟動時自動掃描舵機 ID
  delay(500);  // 等待舵機啟動
  autoDetectServoId();

  Serial.print(F("{\"status\":\"info\",\"message\":\"舵機ID已設置\",\"pan_id\":"));
  Serial.print(panServoId);
  Serial.print(F(",\"tilt_id\":"));
  Serial.print(tiltServoId);
  Serial.println(F("}"));

  // 啟用看門狗定時器（2秒超時）
  wdt_enable(WDTO_2S);
  Serial.println(F("{\"status\":\"info\",\"message\":\"看門狗已啟用 (2秒)\"}"));
}

void loop() {
  // 0) 重置看門狗（防止超時重啟）
  wdt_reset();

  // 1) 檢查聚合命令超時
  if (aggType != AGG_NONE && aggTimeout > 0 && millis() > aggTimeout) {
    sendError("Aggregate command timeout");
    resetAggState();
  }

  // 2) 讀取 PC 指令（以 \n 分隔）
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (pcBufLen > 0) {
        pcBuf[pcBufLen] = '\0';  // 終止字串
        handlePcLine(pcBuf);
        clearBuf(pcBuf, pcBufLen);
      }
    } else {
      if (pcBufLen < sizeof(pcBuf) - 1) {
        pcBuf[pcBufLen++] = c;
      } else {
        // 緩衝區滿，清空並報錯
        clearBuf(pcBuf, pcBufLen);
        sendError("Command too long");
      }
    }
  }

  // 3) 轉發總線回覆
  if (lastBusCmd == BUS_NONE) {
    // 若有聚合狀態，則分階段解析；否則直接透傳
    if (aggType == AGG_NONE) {
      forwardBusResponse();
    } else {
      // 聚合命令解析
      while (BUS_SERIAL.available()) {
        char c = (char)BUS_SERIAL.read();
        if (busBufLen < sizeof(busBuf) - 1) {
          busBuf[busBufLen++] = c;
        }

        if (c == '!' || c == '\n' || c == '\r' || busBufLen >= sizeof(busBuf) - 1) {
          busBuf[busBufLen] = '\0';

          // 提取整數
          int values[4];
          int vcount = 0;
          char* ptr = busBuf;
          char num[16];
          int numLen = 0;

          while (*ptr && vcount < 4) {
            if ((*ptr >= '0' && *ptr <= '9') || *ptr == '-') {
              if (numLen < 15) num[numLen++] = *ptr;
            } else {
              if (numLen > 0) {
                num[numLen] = '\0';
                values[vcount++] = atoi(num);
                numLen = 0;
              }
            }
            ptr++;
          }
          if (numLen > 0 && vcount < 4) {
            num[numLen] = '\0';
            values[vcount++] = atoi(num);
          }

          // 聚合流程
          if (aggType == AGG_POS_BOTH) {
            if (aggPhase == 0 && vcount >= 1) {
              aggPanAngle = values[0];
              aggPhase = 1;
              clearBuf(busBuf, busBufLen);
              char buf[24];
              snprintf(buf, sizeof(buf), "#%03dPRAD!", tiltServoId);
              sendBus(buf);
              break;
            } else if (aggPhase == 1 && vcount >= 1) {
              aggTiltAngle = values[0];
              Serial.print("{\"pan\":");
              Serial.print(aggPanAngle);
              Serial.print(",\"tilt\":");
              Serial.print(aggTiltAngle);
              Serial.println("}");
              resetAggState();
              break;
            } else {
              Serial.print(busBuf);
              resetAggState();
              break;
            }
          } else if (aggType == AGG_STATUS_BOTH) {
            if (aggPhase == 0 && vcount >= 1) {
              aggPanAngle = values[0];
              aggPhase = 1;
              clearBuf(busBuf, busBufLen);
              char buf[24];
              snprintf(buf, sizeof(buf), "#%03dPRTV!", panServoId);
              sendBus(buf);
              break;
            } else if (aggPhase == 1 && vcount >= 2) {
              aggPanVolt = values[0];
              aggPanTemp = values[1];
              aggPhase = 2;
              clearBuf(busBuf, busBufLen);
              char buf[24];
              snprintf(buf, sizeof(buf), "#%03dPRAD!", tiltServoId);
              sendBus(buf);
              break;
            } else if (aggPhase == 2 && vcount >= 1) {
              aggTiltAngle = values[0];
              aggPhase = 3;
              clearBuf(busBuf, busBufLen);
              char buf[24];
              snprintf(buf, sizeof(buf), "#%03dPRTV!", tiltServoId);
              sendBus(buf);
              break;
            } else if (aggPhase == 3 && vcount >= 2) {
              aggTiltVolt = values[0];
              aggTiltTemp = values[1];
              Serial.print("{\"pan\":");
              Serial.print(aggPanAngle);
              Serial.print(",\"tilt\":");
              Serial.print(aggTiltAngle);
              Serial.print(",\"pan_temp\":");
              Serial.print(aggPanTemp);
              Serial.print(",\"tilt_temp\":");
              Serial.print(aggTiltTemp);
              Serial.print(",\"pan_voltage\":");
              Serial.print(aggPanVolt);
              Serial.print(",\"tilt_voltage\":");
              Serial.print(aggTiltVolt);
              Serial.println("}");
              resetAggState();
              break;
            } else {
              Serial.print(busBuf);
              resetAggState();
              break;
            }
          }
        }
      }
    }
  } else {
    // 單次命令回覆解析
    while (BUS_SERIAL.available()) {
      char c = (char)BUS_SERIAL.read();
      if (busBufLen < sizeof(busBuf) - 1) {
        busBuf[busBufLen++] = c;
      }

      if (c == '!' || c == '\n' || c == '\r' || busBufLen >= sizeof(busBuf) - 1) {
        busBuf[busBufLen] = '\0';

        // 提取整數
        int values[4];
        int vcount = 0;
        char* ptr = busBuf;
        char num[16];
        int numLen = 0;

        while (*ptr && vcount < 4) {
          if ((*ptr >= '0' && *ptr <= '9') || *ptr == '-') {
            if (numLen < 15) num[numLen++] = *ptr;
          } else {
            if (numLen > 0) {
              num[numLen] = '\0';
              values[vcount++] = atoi(num);
              numLen = 0;
            }
          }
          ptr++;
        }
        if (numLen > 0 && vcount < 4) {
          num[numLen] = '\0';
          values[vcount++] = atoi(num);
        }

        // 根據最後指令類型輸出 JSON
        if (lastBusCmd == BUS_READ_ANGLE && vcount >= 1) {
          Serial.print("{\"id\":");
          Serial.print(lastBusId);
          Serial.print(",\"angle\":");
          Serial.print(values[0]);
          Serial.println("}");
        } else if (lastBusCmd == BUS_READ_VOLTEMP && vcount >= 2) {
          Serial.print("{\"id\":");
          Serial.print(lastBusId);
          Serial.print(",\"voltage\":");
          Serial.print(values[0]);
          Serial.print(",\"temp\":");
          Serial.print(values[1]);
          Serial.println("}");
        } else {
          // 解析失敗則原樣透傳
          Serial.print(busBuf);
        }

        // 重置狀態
        lastBusCmd = BUS_NONE;
        lastBusId = -1;
        clearBuf(busBuf, busBufLen);
        break;
      }
    }
  }

  delay(5);
}
