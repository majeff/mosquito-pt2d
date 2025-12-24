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
#include "config.h"

#if !defined(__AVR_ATmega2560__)
#include <SoftwareSerial.h>
SoftwareSerial BUS_SERIAL(SERVO_TX_PIN, SERVO_RX_PIN);
#else
#define BUS_SERIAL Serial1
#endif

// LED / BEEP 定義（參照範例）
#define LED_PIN 13
#define BEEP_PIN 4

static String pcBuf;
static String busBuf;

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

static void setup_led() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH); // 熄滅
}

static void setup_beep() {
  pinMode(BEEP_PIN, OUTPUT);
  digitalWrite(BEEP_PIN, HIGH); // 關閉
}

static void setup_uart() {
  Serial.begin(SERIAL_BAUDRATE);
}

static void setup_bus() {
#if !defined(__AVR_ATmega2560__)
  BUS_SERIAL.begin(SERVO_BAUDRATE);
#else
  BUS_SERIAL.begin(SERVO_BAUDRATE);
#endif
}

// 自動掃描舵機 ID
static void autoDetectServoId() {
  if (!AUTO_DETECT_SERVO_ID) {
    servoIdDetected = true;
    return;
  }

  Serial.println("[INFO] 啟動舵機ID自動掃描...");

  // 嘗試掃描 Pan 舵機
  for (int id = 1; id <= 5; id++) {
    char buf[16];
    snprintf(buf, sizeof(buf), "#%03dPID!", id);
    sendBus(String(buf));
    delay(SERVO_DETECT_INTERVAL);

    // 檢查回應
    unsigned long timeout = millis() + SERVO_DETECT_TIMEOUT;
    while (millis() < timeout && BUS_SERIAL.available()) {
      char c = (char)BUS_SERIAL.read();
      if (c == '!') {
        panServoId = id;
        Serial.print("[OK] Pan 舵機 ID: ");
        Serial.println(panServoId);
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
    sendBus(String(buf));
    delay(SERVO_DETECT_INTERVAL);

    // 檢查回應
    unsigned long timeout = millis() + SERVO_DETECT_TIMEOUT;
    while (millis() < timeout && BUS_SERIAL.available()) {
      char c = (char)BUS_SERIAL.read();
      if (c == '!') {
        tiltServoId = id;
        Serial.print("[OK] Tilt 舵機 ID: ");
        Serial.println(tiltServoId);
        break;
      }
    }
  }

  // 清空緩衝區
  while (BUS_SERIAL.available()) {
    BUS_SERIAL.read();
  }

  servoIdDetected = true;
  Serial.println("[INFO] 舵機掃描完成");
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

static void sendBus(const String &cmd) {
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

static void handlePcLine(const String &line) {
  // 1) 直接透傳 #...! 指令到總線
  if (line.startsWith("#")) {
    sendBus(line);
    return;
  }

  // 2) 最小集合：<RAW:...> 直接帶 payload 為 #...! 指令
  if (line.startsWith("<") && line.endsWith(">")) {
    String inner = line.substring(1, line.length() - 1);
    int colon = inner.indexOf(':');
    String cmdType = colon >= 0 ? inner.substring(0, colon) : inner;
    String params = colon >= 0 ? inner.substring(colon + 1) : String("");
    cmdType.toUpperCase();

    if (cmdType == "RAW") {
      // 例如 <RAW:#001P1500T1000!>
      lastBusCmd = BUS_NONE; // 保持透傳，不解析
      lastBusId = -1;
      sendBus(params);
      return;
    }

    if (cmdType == "LED") {
      // <LED:ON> 或 <LED:OFF>
      params.toUpperCase();
      if (params == "ON") digitalWrite(LED_PIN, LOW);
      else digitalWrite(LED_PIN, HIGH);
      Serial.println("{\"status\":\"ok\",\"message\":\"LED\"}");
      return;
    }

    if (cmdType == "BEEP") {
      beep_short3();
      Serial.println("{\"status\":\"ok\",\"message\":\"BEEP\"}");
      return;
    }

    if (cmdType == "SPEED") {
      int val = params.toInt();
      if (val < 1) val = 1; if (val > 100) val = 100;
      moveSpeed = val;
      moveTime = map(moveSpeed, 1, 100, 5000, 100);
      Serial.println("{\"status\":\"ok\",\"message\":\"OK\"}");
      return;
    }

    if (cmdType == "SETID") {
      // 格式：<SETID:pan_id,tilt_id>
      int comma = params.indexOf(',');
      if (comma > 0) {
        int newPanId = params.substring(0, comma).toInt();
        int newTiltId = params.substring(comma + 1).toInt();
        if (newPanId > 0 && newTiltId > 0) {
          panServoId = newPanId;
          tiltServoId = newTiltId;
          Serial.print("{\"status\":\"ok\",\"message\":\"Pan ID=");
          Serial.print(panServoId);
          Serial.print(", Tilt ID=");
          Serial.print(tiltServoId);
          Serial.println("\"}");
          return;
        }
      }
      Serial.println("{\"status\":\"error\",\"message\":\"Invalid parameter\"}");
      return;
    }

    if (cmdType == "MOVE" || cmdType == "MOVETO") {
      // 格式：<MOVE:pan,tilt>
      int comma = params.indexOf(',');
      if (comma > 0) {
        int panAngle = params.substring(0, comma).toInt();
        int tiltAngle = params.substring(comma + 1).toInt();
        uint16_t panPos = angleToPosition(panAngle);
        uint16_t tiltPos = angleToPosition(tiltAngle);
        char buf[32];
        snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, panPos, moveTime);
        sendBus(String(buf));
        snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, tiltPos, moveTime);
        sendBus(String(buf));
        Serial.println("{\"status\":\"ok\",\"message\":\"OK\"}");
        return;
      }
      Serial.println("{\"status\":\"error\",\"message\":\"Invalid parameter\"}");
      return;
    }

    if (cmdType == "STOP") {
      char buf[24];
      snprintf(buf, sizeof(buf), "#%03dPDST!", panServoId);
      sendBus(String(buf));
      snprintf(buf, sizeof(buf), "#%03dPDST!", tiltServoId);
      sendBus(String(buf));
      Serial.println("{\"status\":\"ok\",\"message\":\"OK\"}");
      return;
    }

    if (cmdType == "HOME") {
      uint16_t panPos = angleToPosition(PAN_INIT_ANGLE);
      uint16_t tiltPos = angleToPosition(TILT_INIT_ANGLE);
      char buf[32];
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, panPos, moveTime);
      sendBus(String(buf));
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, tiltPos, moveTime);
      sendBus(String(buf));
      Serial.println("{\"status\":\"ok\",\"message\":\"OK\"}");
      return;
    }

    // 4) 聚合命令：POS（雙軸角度）
    if (cmdType == "POS" || cmdType == "GETPOS") {
      aggType = AGG_POS_BOTH;
      aggPhase = 0;
      aggPanAngle = aggTiltAngle = -1;
      busBuf = "";
      char buf[24];
      snprintf(buf, sizeof(buf), "#%03dPRAD!", panServoId);
      sendBus(String(buf));
      return;
    }

    // 5) 聚合命令：STATUS（雙軸角度+電壓+溫度）
    if (cmdType == "STATUS" || cmdType == "INFO") {
      aggType = AGG_STATUS_BOTH;
      aggPhase = 0;
      aggPanAngle = aggTiltAngle = -1;
      aggPanVolt = aggTiltVolt = -1;
      aggPanTemp = aggTiltTemp = -1;
      busBuf = "";
      char buf[24];
      snprintf(buf, sizeof(buf), "#%03dPRAD!", panServoId);
      sendBus(String(buf));
      return;
    }

    if (cmdType == "READANGLE") {
      // <READANGLE:id>
      int id = params.toInt();
      if (id <= 0) { Serial.println("{\"status\":\"error\",\"message\":\"Invalid parameter\"}"); return; }
      char buf[24];
      snprintf(buf, sizeof(buf), "#%03dPRAD!", id);
      lastBusCmd = BUS_READ_ANGLE;
      lastBusId = id;
      busBuf = "";
      sendBus(String(buf));
      return;
    }

    if (cmdType == "READVOLTEMP") {
      // <READVOLTEMP:id>
      int id = params.toInt();
      if (id <= 0) { Serial.println("{\"status\":\"error\",\"message\":\"Invalid parameter\"}"); return; }
      char buf[24];
      snprintf(buf, sizeof(buf), "#%03dPRTV!", id);
      lastBusCmd = BUS_READ_VOLTEMP;
      lastBusId = id;
      busBuf = "";
      sendBus(String(buf));
      return;
    }

    // 6) MOVER/MOVEBY - 相對移動
    if (cmdType == "MOVER" || cmdType == "MOVEBY") {
      // 格式：<MOVER:pan_delta,tilt_delta>
      int comma = params.indexOf(',');
      if (comma > 0) {
        int panDelta = params.substring(0, comma).toInt();
        int tiltDelta = params.substring(comma + 1).toInt();

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
        sendBus(String(buf));
        snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, tiltPos, moveTime);
        sendBus(String(buf));
        Serial.println("{\"status\":\"ok\",\"message\":\"OK\"}");
        return;
      }
      Serial.println("{\"status\":\"error\",\"message\":\"Invalid parameter\"}");
      return;
    }

    // 7) READ/READPOS - 讀取舵機實際位置（同 POS，但強制重新讀取）
    if (cmdType == "READ" || cmdType == "READPOS") {
      aggType = AGG_POS_BOTH;
      aggPhase = 0;
      aggPanAngle = aggTiltAngle = -1;
      busBuf = "";
      char buf[24];
      snprintf(buf, sizeof(buf), "#%03dPRAD!", panServoId);
      sendBus(String(buf));
      return;
    }

    // 8) TEMP/TEMPERATURE - 讀取雙軸溫度
    if (cmdType == "TEMP" || cmdType == "TEMPERATURE") {
      // 聚合讀取兩個舵機的溫度
      aggType = AGG_STATUS_BOTH;  // 復用 STATUS 流程但只輸出溫度
      aggPhase = 0;
      aggPanAngle = aggTiltAngle = -1;
      aggPanVolt = aggTiltVolt = -1;
      aggPanTemp = aggTiltTemp = -1;
      busBuf = "";
      char buf[24];
      snprintf(buf, sizeof(buf), "#%03dPRTV!", panServoId);
      sendBus(String(buf));
      return;
    }

    // 9) VOLT/VOLTAGE - 讀取雙軸電壓
    if (cmdType == "VOLT" || cmdType == "VOLTAGE") {
      // 聚合讀取兩個舵機的電壓
      aggType = AGG_STATUS_BOTH;  // 復用 STATUS 流程但只輸出電壓
      aggPhase = 0;
      aggPanAngle = aggTiltAngle = -1;
      aggPanVolt = aggTiltVolt = -1;
      aggPanTemp = aggTiltTemp = -1;
      busBuf = "";
      char buf[24];
      snprintf(buf, sizeof(buf), "#%03dPRTV!", panServoId);
      sendBus(String(buf));
      return;
    }

    // 10) CAL/CALIBRATE - 執行校準（測試所有運動範圍）
    if (cmdType == "CAL" || cmdType == "CALIBRATE") {
      // 校準流程：中心→Min Pan→Max Pan→Min Tilt→Max Tilt→初始位置
      // 簡單實現：依序發出移動指令，每個停留 2 秒
      char buf[32];
      // 移動到中心位置 (135°, 90°)，2000ms
      uint16_t centerPan = angleToPosition(135);
      uint16_t centerTilt = angleToPosition(90);
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, centerPan, 2000);
      sendBus(String(buf));
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, centerTilt, 2000);
      sendBus(String(buf));
      delay(2500);

      // Pan 最小 (0°) → 位置 0
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, 0, 2000);
      sendBus(String(buf));
      delay(2500);

      // Pan 最大 (270°) → 位置 1000
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, 1000, 2000);
      sendBus(String(buf));
      delay(2500);

      // Tilt 最小 (0°) → 位置 0
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, 0, 2000);
      sendBus(String(buf));
      delay(2500);

      // Tilt 最大 (180°) → 位置 1000
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, 1000, 2000);
      sendBus(String(buf));
      delay(2500);

      // 回到初始位置
      uint16_t panPos = angleToPosition(PAN_INIT_ANGLE);
      uint16_t tiltPos = angleToPosition(TILT_INIT_ANGLE);
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", panServoId, panPos, 2000);
      sendBus(String(buf));
      snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", tiltServoId, tiltPos, 2000);
      sendBus(String(buf));

      Serial.println("{\"status\":\"ok\",\"message\":\"OK\"}");
      return;
    }

    // 其他 <...> 命令暫不支持；回覆錯誤
    Serial.println("{\"status\":\"error\",\"message\":\"Unknown command\"}");
    return;
  }
}

void setup() {
  setup_led();
  setup_beep();
  setup_uart();
  setup_bus();

  Serial.println(F("================================="));
  Serial.println(F("PT2D Bridge Firmware v2.2.0"));
  Serial.println(F("PC <...> / BUS #...!"));
  Serial.println(F("================================="));
  beep_short3();

  // 啟動時自動掃描舵機 ID
  delay(500);  // 等待舵機啟動
  autoDetectServoId();

  Serial.print(F("[SERVO] Pan ID="));
  Serial.print(panServoId);
  Serial.print(F(" Tilt ID="));
  Serial.println(tiltServoId);
}

void loop() {
  // 讀取 PC 指令（以 \n 分隔）
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (pcBuf.length() > 0) {
        handlePcLine(pcBuf);
        pcBuf = "";
      }
    } else {
      pcBuf += c;
      if (pcBuf.length() > 128) pcBuf = pcBuf.substring(0, 128);
    }
  }

  // 轉發總線回覆
  // 當沒有特別的 READ 命令時，保持透傳；否則嘗試解析一次完整訊息
  if (lastBusCmd == BUS_NONE) {
    // 若有聚合狀態，則分階段解析；否則直接透傳
    if (aggType == AGG_NONE) {
      forwardBusResponse();
    } else {
      while (BUS_SERIAL.available()) {
        char c = (char)BUS_SERIAL.read();
        busBuf += c;
        if (c == '!' || c == '\n' || c == '\r' || busBuf.length() >= 64) {
          // 提取整數
          int values[4];
          int vcount = 0;
          String num = "";
          for (size_t i = 0; i < busBuf.length(); i++) {
            char ch = busBuf[i];
            if ((ch >= '0' && ch <= '9') || ch == '-') {
              num += ch;
            } else {
              if (num.length() > 0 && vcount < 4) {
                values[vcount++] = num.toInt();
                num = "";
              }
            }
          }
          if (num.length() > 0 && vcount < 4) {
            values[vcount++] = num.toInt();
          }

          // 聚合流程
          if (aggType == AGG_POS_BOTH) {
            if (aggPhase == 0 && vcount >= 1) {
              aggPanAngle = values[0];
              aggPhase = 1;
              busBuf = "";
              char buf[24];
              snprintf(buf, sizeof(buf), "#%03dPRAD!", tiltServoId);
              sendBus(String(buf));
              break;
            } else if (aggPhase == 1 && vcount >= 1) {
              aggTiltAngle = values[0];
              Serial.print("{\"pan\":"); Serial.print(aggPanAngle);
              Serial.print(",\"tilt\":"); Serial.print(aggTiltAngle);
              Serial.println("}");
              aggType = AGG_NONE;
              aggPhase = 0;
              busBuf = "";
              break;
            } else {
              Serial.print(busBuf);
              aggType = AGG_NONE;
              aggPhase = 0;
              busBuf = "";
              break;
            }
          } else if (aggType == AGG_STATUS_BOTH) {
            if (aggPhase == 0 && vcount >= 1) {
              aggPanAngle = values[0];
              aggPhase = 1;
              busBuf = "";
              char buf[24];
              snprintf(buf, sizeof(buf), "#%03dPRTV!", PAN_SERVO_ID);
              sendBus(String(buf));
              break;
            } else if (aggPhase == 1 && vcount >= 2) {
              aggPanVolt = values[0];
              aggPanTemp = values[1];
              aggPhase = 2;
              busBuf = "";
              char buf[24];
              snprintf(buf, sizeof(buf), "#%03dPRAD!", tiltServoId);
              sendBus(String(buf));
              break;
            } else if (aggPhase == 2 && vcount >= 1) {
              aggTiltAngle = values[0];
              aggPhase = 3;
              busBuf = "";
              char buf[24];
              snprintf(buf, sizeof(buf), "#%03dPRTV!", tiltServoId);
              sendBus(String(buf));
              break;
            } else if (aggPhase == 3 && vcount >= 2) {
              aggTiltVolt = values[0];
              aggTiltTemp = values[1];
              Serial.print("{\"pan\":"); Serial.print(aggPanAngle);
              Serial.print(",\"tilt\":"); Serial.print(aggTiltAngle);
              Serial.print(",\"pan_temp\":"); Serial.print(aggPanTemp);
              Serial.print(",\"tilt_temp\":"); Serial.print(aggTiltTemp);
              Serial.print(",\"pan_voltage\":"); Serial.print(aggPanVolt);
              Serial.print(",\"tilt_voltage\":"); Serial.print(aggTiltVolt);
              Serial.println("}");
              aggType = AGG_NONE;
              aggPhase = 0;
              busBuf = "";
              break;
            } else {
              Serial.print(busBuf);
              aggType = AGG_NONE;
              aggPhase = 0;
              busBuf = "";
              break;
            }
          }
        }
      }
    }
  } else {
    while (BUS_SERIAL.available()) {
      char c = (char)BUS_SERIAL.read();
      // 累積回覆內容
      busBuf += c;
      // 粗略界定一個回覆結束（遇到 '!' 或換行）
      if (c == '!' || c == '\n' || c == '\r' || busBuf.length() >= 64) {
        // 提取整數
        int values[4];
        int vcount = 0;
        String num = "";
        for (size_t i = 0; i < busBuf.length(); i++) {
          char ch = busBuf[i];
          if ((ch >= '0' && ch <= '9') || ch == '-') {
            num += ch;
          } else {
            if (num.length() > 0 && vcount < 4) {
              values[vcount++] = num.toInt();
              num = "";
            }
          }
        }
        if (num.length() > 0 && vcount < 4) {
          values[vcount++] = num.toInt();
        }

        // 根據最後指令類型輸出 JSON
        if (lastBusCmd == BUS_READ_ANGLE && vcount >= 1) {
          Serial.print("{\"id\":"); Serial.print(lastBusId);
          Serial.print(",\"angle\":"); Serial.print(values[0]);
          Serial.println("}");
        } else if (lastBusCmd == BUS_READ_VOLTEMP && vcount >= 2) {
          Serial.print("{\"id\":"); Serial.print(lastBusId);
          Serial.print(",\"voltage\":"); Serial.print(values[0]);
          Serial.print(",\"temp\":"); Serial.print(values[1]);
          Serial.println("}");
        } else {
          // 解析失敗則原樣透傳
          Serial.print(busBuf);
        }

        // 重置狀態
        lastBusCmd = BUS_NONE;
        lastBusId = -1;
        busBuf = "";
        break; // 本回圈只處理一次完整回覆
      }
    }
  }

  delay(5);
}
