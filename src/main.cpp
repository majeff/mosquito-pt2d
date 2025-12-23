/**
 * @file main.cpp
 * @brief 2D 雲台控制系統主程序
 * @author Arduino PT2D Project
 * @date 2025-12-23
 *
 * 本程序通過 UART (TX/RX) 與上位機通訊，控制 2D 雲台（雙軸伺服馬達）
 */

#include <Arduino.h>
#include "config.h"
#include "ServoController.h"
#include "SerialProtocol.h"

// 全局對象
ServoController servoController;
SerialProtocol serialProtocol;

void setup() {
  // 初始化串口通訊
  Serial.begin(SERIAL_BAUDRATE);
  while (!Serial && millis() < 5000); // 等待串口就緒（最多5秒）

  Serial.println(F("================================="));
  Serial.println(F("Arduino 2D Pan-Tilt Controller"));
  Serial.println(F("Version: 1.0.0"));
  Serial.println(F("================================="));

  // 初始化伺服馬達控制器
  servoController.begin();
  Serial.println(F("Servo controller initialized"));

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

    // 執行命令
    switch (cmd.type) {
      case CMD_MOVE_TO:
        // 移動到指定位置
        servoController.moveTo(cmd.panAngle, cmd.tiltAngle);
        serialProtocol.sendResponse(true, "OK");
        break;

      case CMD_MOVE_BY:
        // 相對移動
        servoController.moveBy(cmd.panAngle, cmd.tiltAngle);
        serialProtocol.sendResponse(true, "OK");
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
        servoController.home();
        serialProtocol.sendResponse(true, "OK");
        break;

      case CMD_STOP:
        // 停止移動
        servoController.stop();
        serialProtocol.sendResponse(true, "OK");
        break;

      case CMD_CALIBRATE:
        // 校準伺服馬達
        servoController.calibrate();
        serialProtocol.sendResponse(true, "OK");
        break;

      default:
        serialProtocol.sendResponse(false, "Unknown command");
        break;
    }
  }

  // 更新伺服馬達（平滑移動）
  servoController.update();

  // 短暫延遲
  delay(10);
}
