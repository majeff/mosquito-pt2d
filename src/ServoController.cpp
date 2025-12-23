/**
 * @file ServoController.cpp
 * @brief 2D 雲台伺服馬達控制器實現
 */

#include "ServoController.h"

ServoController::ServoController()
  : currentPanAngle(PAN_INIT_ANGLE),
    currentTiltAngle(TILT_INIT_ANGLE),
    targetPanAngle(PAN_INIT_ANGLE),
    targetTiltAngle(TILT_INIT_ANGLE),
    moveSpeed(DEFAULT_SPEED),
    lastUpdateTime(0),
    isMoving(false),
    workMode(MODE_MANUAL),
    scanDirection(true),
    lastScanUpdateTime(0) {
  // 計算掃描邊界
  scanMinPan = SCAN_CENTER_PAN - SCAN_RANGE / 2;
  scanMaxPan = SCAN_CENTER_PAN + SCAN_RANGE / 2;
}

void ServoController::begin() {
  // 連接伺服馬達到指定引腳
  panServo.attach(PAN_SERVO_PIN);
  tiltServo.attach(TILT_SERVO_PIN);

  // 移動到初始位置
  panServo.write(currentPanAngle);
  tiltServo.write(currentTiltAngle);

  delay(500); // 等待伺服馬達穩定
}

void ServoController::moveTo(int panAngle, int tiltAngle) {
  // 限制角度範圍
  targetPanAngle = constrainAngle(panAngle, PAN_MIN_ANGLE, PAN_MAX_ANGLE);
  targetTiltAngle = constrainAngle(tiltAngle, TILT_MIN_ANGLE, TILT_MAX_ANGLE);

  isMoving = true;
}

void ServoController::moveBy(int panDelta, int tiltDelta) {
  targetPanAngle = constrainAngle(currentPanAngle + panDelta, PAN_MIN_ANGLE, PAN_MAX_ANGLE);
  targetTiltAngle = constrainAngle(currentTiltAngle + tiltDelta, TILT_MIN_ANGLE, TILT_MAX_ANGLE);

  isMoving = true;
}

void ServoController::home() {
  moveTo(PAN_INIT_ANGLE, TILT_INIT_ANGLE);
}

void ServoController::stop() {
  targetPanAngle = currentPanAngle;
  targetTiltAngle = currentTiltAngle;
  isMoving = false;
}

void ServoController::calibrate() {
  // 簡單校準：回到初始位置
  home();
  Serial.println(F("Calibration complete"));
}

int ServoController::constrainAngle(int angle, int minAngle, int maxAngle) {
  return constrain(angle, minAngle, maxAngle);
}

void ServoController::setMode(int mode) {
  workMode = (mode == 1) ? 1 : 0;

  if (workMode == 1) {
    // 切換到自動掃描模式：固定 Tilt 並開始掃描
    currentTiltAngle = SCAN_TILT_ANGLE;
    targetTiltAngle = SCAN_TILT_ANGLE;
    tiltServo.write(currentTiltAngle);

    // 設置為掃描中心開始
    currentPanAngle = SCAN_CENTER_PAN;
    targetPanAngle = SCAN_CENTER_PAN;
    panServo.write(currentPanAngle);

    scanDirection = true;
    lastScanUpdateTime = millis();
  }
}

int ServoController::getMode() const {
  return workMode;
}

void ServoController::updateAutoScan() {
  if (workMode != 1) return;  // 只在自動掃描模式下執行

  unsigned long currentTime = millis();

  // 檢查是否到達更新間隔
  if (currentTime - lastScanUpdateTime >= SCAN_UPDATE_INTERVAL) {
    lastScanUpdateTime = currentTime;

    // 根據方向更新 Pan 角度
    if (scanDirection) {
      currentPanAngle += SCAN_SPEED / 10;  // 慢速增加
      if (currentPanAngle >= scanMaxPan) {
        currentPanAngle = scanMaxPan;
        scanDirection = false;  // 改變方向
      }
    } else {
      currentPanAngle -= SCAN_SPEED / 10;  // 慢速減少
      if (currentPanAngle <= scanMinPan) {
        currentPanAngle = scanMinPan;
        scanDirection = true;  // 改變方向
      }
    }

    // 限制角度並寫入伺服馬達
    currentPanAngle = constrainAngle(currentPanAngle, PAN_MIN_ANGLE, PAN_MAX_ANGLE);
    panServo.write(currentPanAngle);
  }
}

int ServoController::getPanAngle() const {
  return currentPanAngle;
}

int ServoController::getTiltAngle() const {
  return currentTiltAngle;
}

void ServoController::setSpeed(int speed) {
  moveSpeed = constrain(speed, MIN_SPEED, MAX_SPEED);
}

void ServoController::update() {
  // 平滑移動更新
  if (isMoving) {
    smoothMove();
  }

  // 掃描模式更新
  if (workMode == MODE_AUTO_SCAN) {
    updateAutoScan();
  }
}

void ServoController::smoothMove() {
  bool panReached = (currentPanAngle == targetPanAngle);
  bool tiltReached = (currentTiltAngle == targetTiltAngle);

  // Pan 軸移動
  if (!panReached) {
    if (currentPanAngle < targetPanAngle) {
      currentPanAngle++;
    } else if (currentPanAngle > targetPanAngle) {
      currentPanAngle--;
    }
    panServo.write(currentPanAngle);
  }

  // Tilt 軸移動
  if (!tiltReached) {
    if (currentTiltAngle < targetTiltAngle) {
      currentTiltAngle++;
    } else if (currentTiltAngle > targetTiltAngle) {
      currentTiltAngle--;
    }
    tiltServo.write(currentTiltAngle);
  }

  // 檢查是否到達目標位置
  if (panReached && tiltReached) {
    isMoving = false;
  }
}
