/**
 * @file arduino-pt2d.ino
 * @brief 2D 雲台控制系統主程序 (Arduino IDE 版本)
 * @author Arduino PT2D Project
 * @date 2025-12-23
 *
 * 本程序通過 UART (TX/RX) 與上位機通訊，使用總線舵機控制 2D 雲台
 * 支援 LewanSoul LX-16A, Feetech SCS 系列等總線舵機
 */

#include "config.h"
#include "BusServoController.h"
#include "SerialProtocol.h"

// 全局對象
BusServoController servoController;
SerialProtocol serialProtocol;

// 工作模式
WorkMode currentMode = MODE_MANUAL;

// 自動掃描參數
const int SCAN_TILT_ANGLE = 90;      // 垂直固定角度
const int SCAN_CENTER_PAN = 135;     // 掃描中心
const int SCAN_RANGE = 120;          // 掃描範圍（左右各60度）
const int SCAN_MIN_PAN = SCAN_CENTER_PAN - SCAN_RANGE / 2;  // 75度
const int SCAN_MAX_PAN = SCAN_CENTER_PAN + SCAN_RANGE / 2;  // 195度
int scanDirection = 1;               // 掃描方向：1=向右，-1=向左
unsigned long lastScanUpdate = 0;
const int SCAN_UPDATE_INTERVAL = 100; // 掃描更新間隔（毫秒）

void setup() {
  // 初始化上位機串口通訊
  Serial.begin(SERIAL_BAUDRATE);
  while (!Serial && millis() < 3000); // 等待串口就緒（最多3秒）

  Serial.println(F("================================="));
  Ser設置初始模式
  currentMode = MODE_MANUAL;
  Serial.println(F("Mode: MANUAL"));

  // ial.println(F("Arduino 2D Pan-Tilt Controller"));
  Serial.println(F("Bus Servo Version"));
  Serial.println(F("Version: 1.0.0"));
  Serial.println(F("================================="));

  // 初始化總線舵機控制器
  servoController.begin();
  Serial.println(F("Bus servo controller initialized"));

  // 初始化串口協議
  serialProtocol.begin();
  Serial.println(F("Serial protocol initialized"));

  // 移動到初始位置
  servoController.moveTo(PAN_INIT_ANGLE, TILT_INIT_ANGLE);
  Serial.println(F("Moving to initial position"));
  Serial.println(F("System ready!"));
  Serial.println();
}

void loop() {
  // 處理串口接收的命令
  if (serialProtocol.processIncoming()) {
    // 獲取解析後的命令
    Command cmd = serialProtocol.getLastCommand();
    手動模式才允許移動命令
        if (currentMode == MODE_MANUAL) {
          servoController.moveTo(cmd.panAngle, cmd.tiltAngle);
          serialProtocol.sendResponse(true, "OK");
        } else {
          serialProtocol.sendResponse(false, "Not in manual mode");
        }
        break;

      case CMD_MOVE_BY:
        // 手動模式才允許相對移動
        if (currentMode == MODE_MANUAL) {
          servoController.moveBy(cmd.panAngle, cmd.tiltAngle);
          serialProtocol.sendResponse(true, "OK");
        } else {
          serialProtocol.sendResponse(false, "Not in manual mode");
        }
        break;

      case CMD_GET_POS:
        // 獲取當前位置
        {
          int pan = servoController.getPanAngle();
          int tilt = servoController.getTiltAngle();
          serialProtocol.sendPosition(pan, tilt);
        }
        break;

      case CMD_SET_SPEED:
        // 設置移動速度
        servoController.setSpeed(cmd.speed);
        serialProtocol.sendResponse(true, "OK");
        break;

      case CMD_HOME:
        // 回到初始位置
        if (currentMode == MODE_MANUAL) {
          servoController.home();
          serialProtocol.sendResponse(true, "OK");
        } else {
          serialProtocol.sendResponse(false, "Not in manual mode");
        }
        break;

      case CMD_STOP:
        // 停止移動（任何模式都可以）
        servoController.stop();
        serialProtocol.sendResponse(true, "OK");
        break;

      case CMD_CALIBRATE:
        // 校準伺服馬達
        if (currentMode == MODE_MANUAL) {
          servoController.calibrate();
          serialProtocol.sendResponse(true, "OK");
        } else {
          serialProtocol.sendResponse(false, "Not in manual mode");
        }
        break;

      case CMD_READ_POS:
        // 讀取舵機實際位置
        {
          int pan = servoController.readPanPosition();
          int tilt = servoController.readTiltPosition();
          serialProtocol.sendPosition(pan, tilt);
        }
        break;

      case CMD_SET_MODE:
        // 切換工作模式
        if (cmd.mode == 0) {
          currentMode = MODE_MANUAL;
          Serial.println(F("Switched to MANUAL mode"));
          serialProtocol.sendResponse(true, "Manual mode");
        } else if (cmd.mode == 1) {
          currentMode = MODE_AUTO_SCAN;
          // 初始化自動掃描
          servoController.setSpeed(20);  // 設置慢速
          servoController.moveTo(SCAN_MIN_PAN, SCAN_TILT_ANGLE);
          scanDirection = 1;
          lastScanUpdate = millis();
          Serial.println(F("Switched to AUTO SCAN mode"));
          serialProtocol.sendResponse(true, "Auto scan mode");
        } else {
          serialProtocol.sendResponse(false, "Invalid mode");
        }
        break;

      case CMD_GET_MODE:
        // 獲取當前模式
        {
          Serial.print(F("{\"mode\":"));
          Serial.print(currentMode);
          Serial.print(F(",\"name\":\""));
          Serial.print(currentMode == MODE_MANUAL ? F("MANUAL") : F("AUTO_SCAN"));
          Serial.println(F("\"}"));
        }
        break;

      case CMD_READ_TEMP:
        // 讀取舵機溫度
        {
          int panTemp = servoController.readPanTemperature();
          int tiltTemp = servoController.readTiltTemperature();
          serialProtocol.sendTemperature(panTemp, tiltTemp);
        }
        break;

      case CMD_READ_VOLTAGE:
        // 讀取舵機電壓
        {
          int panVolt = servoController.readPanVoltage();
          int tiltVolt = servoController.readTiltVoltage();
          serialProtocol.sendVoltage(panVolt, tiltVolt);
        }
        break;

      case CMD_READ_STATUS:
        // 讀取完整狀態
        {
          int pan = servoController.readPanPosition();
          int tilt = servoController.readTiltPosition();
          int panTemp = servoController.readPanTemperature();
          int tiltTemp = servoController.readTiltTemperature();
          int panVolt = servoController.readPanVoltage();
          int tiltVolt = servoController.readTiltVoltage();
          serialProtocol.sendFullStatus(pan, tilt, panTemp, tiltTemp, panVolt, tiltVolt);
        }
        break;

      default:
        serialProtocol.sendResponse(false, "Unknown command");
        break;
    }
  }

  // 自動掃描模式處理
  if (currentMode == MODE_AUTO_SCAN) {
    unsigned long currentTime = millis();
    if (currentTime - lastScanUpdate >= SCAN_UPDATE_INTERVAL) {
      lastScanUpdate = currentTime;

      // 獲取當前位置
      int currentPan = servoController.getPanAngle();

      // 計算下一個位置
      int nextPan = currentPan + scanDirection;

      // 檢查是否到達邊界
      if (nextPan >= SCAN_MAX_PAN) {
        nextPan = SCAN_MAX_PAN;
        scanDirection = -1;  // 改變方向
      } else if (nextPan <= SCAN_MIN_PAN) {
        nextPan = SCAN_MIN_PAN;
        scanDirection = 1;   // 改變方向
      }

      // 移動到下一個位置
      servoController.moveTo(nextPan, SCAN_TILT_ANGLE);

      default:
        serialProtocol.sendResponse(false, "Unknown command");
        break;
    }
  }

  // 短暫延遲
  delay(10);
}
