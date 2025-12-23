/**
 * @file ServoController.h
 * @brief 2D 雲台伺服馬達控制器
 * @details 控制 Pan (水平) 和 Tilt (垂直) 兩個軸的伺服馬達
 */

#ifndef SERVO_CONTROLLER_H
#define SERVO_CONTROLLER_H

#include <Arduino.h>
#include <Servo.h>
#include "config.h"

class ServoController {
public:
  /**
   * @brief 構造函數
   */
  ServoController();

  /**
   * @brief 初始化伺服馬達
   */
  void begin();

  /**
   * @brief 移動到絕對位置
   * @param panAngle Pan 軸角度 (0-180)
   * @param tiltAngle Tilt 軸角度 (0-180)
   */
  void moveTo(int panAngle, int tiltAngle);

  /**
   * @brief 相對移動
   * @param panDelta Pan 軸相對角度變化
   * @param tiltDelta Tilt 軸相對角度變化
   */
  void moveBy(int panDelta, int tiltDelta);

  /**
   * @brief 回到初始位置
   */
  void home();

  /**
   * @brief 停止移動
   */
  void stop();

  /**
   * @brief 設置移動速度
   * @param speed 速度 (1-100, 100為最快)
   */
  void setSpeed(int speed);

  /**
   * @brief 獲取當前 Pan 角度
   * @return 當前 Pan 角度
   */
  int getPanAngle() const;

  /**
   * @brief 獲取當前 Tilt 角度
   * @return 當前 Tilt 角度
   */
  int getTiltAngle() const;

  /**
   * @brief 更新函數（用於平滑移動）
   * @details 在 loop() 中調用以實現平滑移動
   */
  void update();

  /**
   * @brief 校準伺服馬達
   */
  void calibrate();

  /**
   * @brief 設置工作模式
   * @param mode 0=手動, 1=自動掃描
   */
  void setMode(int mode);

  /**
   * @brief 獲取當前工作模式
   * @return 0=手動, 1=自動掃描
   */
  int getMode() const;

  /**
   * @brief 自動掃描更新（在掃描模式下呼叫）
   */
  void updateAutoScan();

private:
  Servo panServo;    // Pan 軸伺服馬達
  Servo tiltServo;   // Tilt 軸伺服馬達

  int currentPanAngle;   // 當前 Pan 角度
  int currentTiltAngle;  // 當前 Tilt 角度

  int targetPanAngle;    // 目標 Pan 角度
  int targetTiltAngle;   // 目標 Tilt 角度

  int moveSpeed;         // 移動速度 (1-100)
  unsigned long lastUpdateTime; // 上次更新時間

  bool isMoving;         // 是否正在移動

  // 工作模式/掃描狀態
  int workMode;              // 0=手動, 1=自動掃描
  bool scanDirection;        // 掃描方向
  unsigned long lastScanUpdateTime; // 掃描上次更新時間
  int scanMinPan;            // 掃描最小 Pan
  int scanMaxPan;            // 掃描最大 Pan

  /**
   * @brief 限制角度範圍
   * @param angle 輸入角度
   * @param minAngle 最小角度
   * @param maxAngle 最大角度
   * @return 限制後的角度
   */
  int constrainAngle(int angle, int minAngle, int maxAngle);

  /**
   * @brief 平滑移動到目標位置
   */
  void smoothMove();
};

#endif // SERVO_CONTROLLER_H
