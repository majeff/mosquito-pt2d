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
    moveSpeed(50),
    lastUpdateTime(0),
    isMoving(false) {
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

void ServoController::setSpeed(int speed) {
  moveSpeed = constrain(speed, 1, 100);
}

int ServoController::getPanAngle() const {
  return currentPanAngle;
}

int ServoController::getTiltAngle() const {
  return currentTiltAngle;
}

void ServoController::update() {
  unsigned long currentTime = millis();

  // 根據速度控制更新頻率
  unsigned long updateInterval = map(moveSpeed, 1, 100, 100, 10);

  if (currentTime - lastUpdateTime >= updateInterval) {
    lastUpdateTime = currentTime;

    if (isMoving) {
      smoothMove();
    }
  }
}

void ServoController::calibrate() {
  // 校準程序：移動到各個極限位置
  Serial.println(F("Calibrating..."));

  // 移動到中心位置
  moveTo(90, 90);
  delay(1000);

  // 測試 Pan 軸
  moveTo(PAN_MIN_ANGLE, 90);
  delay(1000);
  moveTo(PAN_MAX_ANGLE, 90);
  delay(1000);

  // 測試 Tilt 軸
  moveTo(90, TILT_MIN_ANGLE);
  delay(1000);
  moveTo(90, TILT_MAX_ANGLE);
  delay(1000);

  // 回到初始位置
  home();

  Serial.println(F("Calibration complete"));
}

int ServoController::constrainAngle(int angle, int minAngle, int maxAngle) {
  return constrain(angle, minAngle, maxAngle);
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
