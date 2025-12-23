/**
 * @file BusServoController.h
 * @brief 2D 雲台總線舵機控制器
 * @details 控制 Pan (水平) 和 Tilt (垂直) 兩個軸的總線舵機
 * 支援 LewanSoul LX-16A, Feetech SCS 系列等
 */

#ifndef BUS_SERVO_CONTROLLER_H
#define BUS_SERVO_CONTROLLER_H

#include <Arduino.h>
#include "config.h"

// LewanSoul/Lobot 舵機命令
#define SERVO_MOVE_TIME_WRITE  1   // 移動指令
#define SERVO_MOVE_TIME_READ   2   // 讀取位置
#define SERVO_MOVE_START       11  // 開始移動
#define SERVO_MOVE_STOP        12  // 停止移動
#define SERVO_ID_WRITE         13  // 修改 ID
#define SERVO_ANGLE_OFFSET     14  // 角度偏移
#define SERVO_VIN_READ         27  // 讀取電壓
#define SERVO_TEMP_READ        26  // 讀取溫度
#define SERVO_POS_READ         28  // 讀取當前位置

class BusServoController {
public:
  /**
   * @brief 構造函數
   */
  BusServoController();

  /**
   * @brief 初始化總線舵機
   */
  void begin();

  /**
   * @brief 移動到絕對位置
   * @param panAngle Pan 軸角度 (0-180 或 0-240，視舵機而定)
   * @param tiltAngle Tilt 軸角度 (0-180 或 0-240)
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
   * @brief 獲取當前 Pan 角度（緩存值）
   * @return 當前 Pan 角度
   */
  int getPanAngle() const;

  /**
   * @brief 獲取當前 Tilt 角度（緩存值）
   * @return 當前 Tilt 角度
   */
  int getTiltAngle() const;

  /**
   * @brief 讀取 Pan 舵機實際位置
   * @return 實際 Pan 角度
   */
  int readPanPosition();

  /**
   * @brief 讀取 Tilt 舵機實際位置
   * @return 實際 Tilt 角度
   */
  int readTiltPosition();
  讀取 Pan 舵機溫度
   * @return 溫度（攝氏度），失敗返回 -1
   */
  int readPanTemperature();

  /**
   * @brief 讀取 Tilt 舵機溫度
   * @return 溫度（攝氏度），失敗返回 -1
   */
  int readTiltTemperature();

  /**
   * @brief 讀取 Pan 舵機電壓
   * @return 電壓（毫伏 mV），失敗返回 -1
   */
  int readPanVoltage();

  /**
   * @brief 讀取 Tilt 舵機電壓
   * @return 電壓（毫伏 mV），失敗返回 -1
   */
  int readTiltVoltage();

  /**
   * @brief
  /**
   * @brief 校準舵機
   */
  void calibrate();

private:
  int currentPanAngle;   // 當前 Pan 角度
  int currentTiltAngle;  // 當前 Tilt 角度
  int moveSpeed;         // 移動速度 (1-100)
  int moveTime;          // 移動時間 (毫秒)

  /**
   * @brief 限制角度範圍
   * @param angle 輸入角度
   * @param minAngle 最小角度
   * @param maxAngle 最大角度
   * @return 限制後的角度
   */
  int constr讀取舵機溫度
   * @param id 舵機 ID
   * @return 溫度（攝氏度），失敗返回 -1
   */
  int servoReadTemperature(uint8_t id);

  /**
   * @brief 讀取舵機電壓
   * @param id 舵機 ID
   * @return 電壓（毫伏 mV），失敗返回 -1
   */
  int servoReadVoltage(uint8_t id);

  /**
   * @brief ainAngle(int angle, int minAngle, int maxAngle);

  /**
   * @brief 發送舵機移動命令
   * @param id 舵機 ID
   * @param position 目標位置 (0-1000)
   * @param time 移動時間 (毫秒)
   */
  void servoMove(uint8_t id, uint16_t position, uint16_t time);

  /**
   * @brief 發送舵機停止命令
   * @param id 舵機 ID
   */
  void servoStop(uint8_t id);

  /**
   * @brief 讀取舵機當前位置
   * @param id 舵機 ID
   * @return 當前位置 (0-1000)，失敗返回 -1
   */
  int servoReadPosition(uint8_t id);

  /**
   * @brief 計算校驗和
   * @param buf 數據緩衝區
   * @param len 數據長度
   * @return 校驗和
   */
  uint8_t calculateChecksum(uint8_t *buf, uint8_t len);

  /**
   * @brief 發送數據包
   * @param buf 數據緩衝區
   * @param len 數據長度
   */
  void sendPacket(uint8_t *buf, uint8_t len);

  /**
   * @brief 接收數據包
   * @param buf 數據緩衝區
   * @param timeout 超時時間（毫秒）
   * @return 接收到的字節數
   */
  int receivePacket(uint8_t *buf, int timeout);

  /**
   * @brief 角度轉換為舵機位置值
   * @param angle 角度 (0-180 或 0-240)
   * @return 位置值 (0-1000)
   */
  uint16_t angleToPosition(int angle);

  /**
   * @brief 舵機位置值轉換為角度
   * @param position 位置值 (0-1000)
   * @return 角度 (0-180 或 0-240)
   */
  int positionToAngle(uint16_t position);
};

#endif // BUS_SERVO_CONTROLLER_H
