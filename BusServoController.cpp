/**
 * @file BusServoController.cpp
 * @brief 2D 雲台總線舵機控制器實現
 * 支援 LewanSoul LX-16A, Feetech SCS 系列
 */

#include "BusServoController.h"

BusServoController::BusServoController()
  : currentPanAngle(PAN_INIT_ANGLE),
    currentTiltAngle(TILT_INIT_ANGLE),
    moveSpeed(50),
    moveTime(1000) {
}

void BusServoController::begin() {
  // 初始化舵機串口
  SERVO_SERIAL.begin(SERVO_BAUDRATE);

  delay(100);

  // 移動到初始位置
  moveTo(currentPanAngle, currentTiltAngle);

  delay(500); // 等待舵機穩定
}

void BusServoController::moveTo(int panAngle, int tiltAngle) {
  // 限制角度範圍
  currentPanAngle = constrainAngle(panAngle, PAN_MIN_ANGLE, PAN_MAX_ANGLE);
  currentTiltAngle = constrainAngle(tiltAngle, TILT_MIN_ANGLE, TILT_MAX_ANGLE);

  // 轉換角度到位置值
  uint16_t panPos = angleToPosition(currentPanAngle);
  uint16_t tiltPos = angleToPosition(currentTiltAngle);

  // 發送移動命令
  servoMove(PAN_SERVO_ID, panPos, moveTime);
  delay(10);
  servoMove(TILT_SERVO_ID, tiltPos, moveTime);
}

void BusServoController::moveBy(int panDelta, int tiltDelta) {
  int newPan = constrainAngle(currentPanAngle + panDelta, PAN_MIN_ANGLE, PAN_MAX_ANGLE);
  int newTilt = constrainAngle(currentTiltAngle + tiltDelta, TILT_MIN_ANGLE, TILT_MAX_ANGLE);

  moveTo(newPan, newTilt);
}

void BusServoController::home() {
  moveTo(PAN_INIT_ANGLE, TILT_INIT_ANGLE);
}

void BusServoController::stop() {
  servoStop(PAN_SERVO_ID);
  delay(10);
  servoStop(TILT_SERVO_ID);
}

void BusServoController::setSpeed(int speed) {
  moveSpeed = constrain(speed, 1, 100);
  // 速度映射到移動時間 (速度越快，時間越短)
  // 速度 1 = 5000ms, 速度 100 = 100ms
  moveTime = map(moveSpeed, 1, 100, 5000, 100);
}

int BusServoController::getPanAngle() const {
  return currentPanAngle;
}

int BusServoController::getTiltAngle() const {
  return currentTiltAngle;
}

int BusServoController::readPanPosition() {
  int pos = servoReadPosition(PAN_SERVO_ID);
  if (pos >= 0) {
    currentPanAngle = positionToAngle(pos);
    return currentPanAngle;
  }
  return currentPanAngle; // 讀取失敗返回緩存值
}

int BusServoController::readTiltPosition() {
  int pos = servoReadPosition(TILT_SERVO_ID);
  if (pos >= 0) {
    currentTiltAngle = positionToAngle(pos);
    return currentTiltAngle;
  }
  return currentTiltAngle; // 讀取失敗返回緩存值
}

int BusServoController::readPanTemperature() {
  return servoReadTemperature(PAN_SERVO_ID);
}

int BusServoController::readTiltTemperature() {
  return servoReadTemperature(TILT_SERVO_ID);
}

int BusServoController::readPanVoltage() {
  return servoReadVoltage(PAN_SERVO_ID);
}

int BusServoController::readTiltVoltage() {
  return servoReadVoltage(TILT_SERVO_ID);
}

void BusServoController::calibrate() {
  Serial.println(F("Calibrating bus servos..."));

  setSpeed(30);

  // 移動到中心位置
  moveTo(90, 90);
  delay(2000);

  // 測試 Pan 軸
  moveTo(PAN_MIN_ANGLE, 90);
  delay(2000);
  moveTo(PAN_MAX_ANGLE, 90);
  delay(2000);

  // 測試 Tilt 軸
  moveTo(90, TILT_MIN_ANGLE);
  delay(2000);
  moveTo(90, TILT_MAX_ANGLE);
  delay(2000);

  // 回到初始位置
  home();
  delay(2000);

  setSpeed(50);

  Serial.println(F("Calibration complete"));
}

int BusServoController::constrainAngle(int angle, int minAngle, int maxAngle) {
  return constrain(angle, minAngle, maxAngle);
}

void BusServoController::servoMove(uint8_t id, uint16_t position, uint16_t time) {
  uint8_t buf[10];

  buf[0] = 0x55;                    // 幀頭 1
  buf[1] = 0x55;                    // 幀頭 2
  buf[2] = id;                      // 舵機 ID
  buf[3] = 7;                       // 數據長度
  buf[4] = SERVO_MOVE_TIME_WRITE;   // 命令
  buf[5] = position & 0xFF;         // 位置低字節
  buf[6] = (position >> 8) & 0xFF;  // 位置高字節
  buf[7] = time & 0xFF;             // 時間低字節
  buf[8] = (time >> 8) & 0xFF;      // 時間高字節
  buf[9] = calculateChecksum(buf, 9);

  sendPacket(buf, 10);
}

void BusServoController::servoStop(uint8_t id) {
  uint8_t buf[6];

  buf[0] = 0x55;                  // 幀頭 1
  buf[1] = 0x55;                  // 幀頭 2
  buf[2] = id;                    // 舵機 ID
  buf[3] = 3;                     // 數據長度
  buf[4] = SERVO_MOVE_STOP;       // 命令
  buf[5] = calculateChecksum(buf, 5);

  sendPacket(buf, 6);
}

int BusServoController::servoReadPosition(uint8_t id) {
  uint8_t buf[6];

  // 發送讀取命令
  buf[0] = 0x55;                  // 幀頭 1
  buf[1] = 0x55;                  // 幀頭 2
  buf[2] = id;                    // 舵機 ID
  buf[3] = 3;                     // 數據長度
  buf[4] = SERVO_POS_READ;        // 命令
  buf[5] = calculateChecksum(buf, 5);

  sendPacket(buf, 6);

  // 接收響應
int BusServoController::servoReadTemperature(uint8_t id) {
  uint8_t buf[6];

  // 發送讀取溫度命令
  buf[0] = 0x55;                  // 幀頭 1
  buf[1] = 0x55;                  // 幀頭 2
  buf[2] = id;                    // 舵機 ID
  buf[3] = 3;                     // 數據長度
  buf[4] = SERVO_TEMP_READ;       // 命令
  buf[5] = calculateChecksum(buf, 5);

  sendPacket(buf, 6);

  // 接收響應
  uint8_t response[8];
  int len = receivePacket(response, 100);

  if (len >= 7 && response[0] == 0x55 && response[1] == 0x55) {
    // 檢查校驗和
    uint8_t checksum = calculateChecksum(response, len - 1);
    if (checksum == response[len - 1]) {
      // 提取溫度（單字節）
      uint8_t temp = response[5];
      return temp;
    }
  }

  return -1; // 讀取失敗
}

int BusServoController::servoReadVoltage(uint8_t id) {
  uint8_t buf[6];

  // 發送讀取電壓命令
  buf[0] = 0x55;                  // 幀頭 1
  buf[1] = 0x55;                  // 幀頭 2
  buf[2] = id;                    // 舵機 ID
  buf[3] = 3;                     // 數據長度
  buf[4] = SERVO_VIN_READ;        // 命令
  buf[5] = calculateChecksum(buf, 5);

  sendPacket(buf, 6);

  // 接收響應
  uint8_t response[8];
  int len = receivePacket(response, 100);

  if (len >= 8 && response[0] == 0x55 && response[1] == 0x55) {
    // 檢查校驗和
    uint8_t checksum = calculateChecksum(response, len - 1);
    if (checksum == response[len - 1]) {
      // 提取電壓（雙字節，單位 mV）
      uint16_t voltage = response[5] | (response[6] << 8);
      return voltage;
    }
  }

  return -1; // 讀取失敗
}

  uint8_t response[10];
  int len = receivePacket(response, 100);

  if (len >= 8 && response[0] == 0x55 && response[1] == 0x55) {
    // 檢查校驗和
    uint8_t checksum = calculateChecksum(response, len - 1);
    if (checksum == response[len - 1]) {
      // 提取位置
      uint16_t position = response[5] | (response[6] << 8);
      return position;
    }
  }

  return -1; // 讀取失敗
}

uint8_t BusServoController::calculateChecksum(uint8_t *buf, uint8_t len) {
  uint8_t sum = 0;
  for (uint8_t i = 2; i < len; i++) {
    sum += buf[i];
  }
  return ~sum;
}

void BusServoController::sendPacket(uint8_t *buf, uint8_t len) {
  // 清空接收緩衝區
  while (SERVO_SERIAL.available()) {
    SERVO_SERIAL.read();
  }

  // 發送數據
  SERVO_SERIAL.write(buf, len);
  SERVO_SERIAL.flush();
}

int BusServoController::receivePacket(uint8_t *buf, int timeout) {
  unsigned long startTime = millis();
  int index = 0;

  while (millis() - startTime < timeout) {
    if (SERVO_SERIAL.available()) {
      buf[index++] = SERVO_SERIAL.read();
      if (index >= 10) break; // 防止溢出
    }
  }

  return index;
}

uint16_t BusServoController::angleToPosition(int angle) {
  // 總線舵機位置值通常為 0-1000
  // 根據舵機實際範圍映射（Pan:0-270°, Tilt:0-180°）
  return map(angle, 0, SERVO_MAX_ANGLE, 0, 1000);
}

int BusServoController::positionToAngle(uint16_t position) {
  // 將位置值轉換回角度
  return map(position, 0, 1000, 0, SERVO_MAX_ANGLE);
}
