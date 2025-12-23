/**
 * @file SerialProtocol.h
 * @brief 串口通訊協議處理器
 * @details 處理與上位機的 UART 通訊，解析命令並發送響應
 *
 * 協議格式：
 * 命令格式: <CMD:param1,param2,...>\n
 * 響應格式: {status:message}\n
 */

#ifndef SERIAL_PROTOCOL_H
#define SERIAL_PROTOCOL_H

#include <Arduino.h>
#include "config.h"

// 命令類型枚舉
enum CommandType {
  CMD_NONE = 0,
  CMD_MOVE_TO,      // 移動到絕對位置: <MOVE:pan,tilt>
  CMD_MOVE_BY,      // 相對移動: <MOVER:pan,tilt>
  CMD_GET_POS,      // 獲取當前位置: <POS>
  CMD_SET_SPEED,    // 設置速度: <SPEED:value>
  CMD_HOME,         // 回到初始位置: <HOME>
  CMD_STOP,         // 停止移動: <STOP>
  CMD_CALIBRATE,    // 校準: <CAL>
  CMD_READ_POS,     // 讀取舵機實際位置: <READ>
  CMD_SET_MODE,     // 設置模式: <MODE:0/1>
  CMD_GET_MODE,     // 獲取當前模式: <GETMODE>
  CMD_READ_TEMP,    // 讀取溫度: <TEMP>
  CMD_READ_VOLTAGE, // 讀取電壓: <VOLT>
  CMD_READ_STATUS   // 讀取狀態（位置+溫度+電壓）: <STATUS>
};

// 工作模式枚舉
enum WorkMode {
  MODE_MANUAL = 0,    // 手動模式
  MODE_AUTO_SCAN = 1  // 自動掃描模式
};

// 命令結構體
struct Command {
  CommandType type;
  int panAngle;
  int tiltAngle;
  int speed;
  int mode;

  Command() : type(CMD_NONE), panAngle(0), tiltAngle(0), speed(0), mode(0) {}
};

class SerialProtocol {
public:
  /**
   * @brief 構造函數
   */
  SerialProtocol();

  /**
   * @brief 初始化串口協議
   */
  void begin();

  /**
   * @brief 處理接收的串口數據
   * @return 是否成功解析出完整命令
   */
  bool processIncoming();

  /**
   * @brief 獲取最後解析的命令
   * @return 命令結構體
   */
  Command getLastCommand() const;

  /**
   * @brief 發送響應消息
   * @param success 是否成功
   * @param message 消息內容
   */
  void sendResponse(bool success, const char* message);

  /**
   * @brief 發送當前位置
   * @param panAngle Pan 角度
   * @param tiltAngle Tilt 角度
   */
  void sendPosition(int panAngle, int tiltAngle);

  /**
   * @brief 發送狀態信息
   * @param status 狀態字符串
  /**
   * @brief 發送溫度信息
   * @param panTemp Pan 軸溫度
   * @param tiltTemp Tilt 軸溫度
   */
  void sendTemperature(int panTemp, int tiltTemp);

  /**
   * @brief 發送電壓信息
   * @param panVolt Pan 軸電壓（mV）
   * @param tiltVolt Tilt 軸電壓（mV）
   */
  void sendVoltage(int panVolt, int tiltVolt);

  /**
   * @brief 發送完整狀態（位置+溫度+電壓）
   * @param pan Pan 角度
   * @param tilt Tilt 角度
   * @param panTemp Pan 溫度
   * @param tiltTemp Tilt 溫度
   * @param panVolt Pan 電壓
   * @param tiltVolt Tilt 電壓
   */
  void sendFullStatus(int pan, int tilt, int panTemp, int tiltTemp, int panVolt, int tiltVolt);

   */
  void sendStatus(const char* status);

private:
  String receiveBuffer;  // 接收緩衝區
  Command lastCommand;   // 最後解析的命令

  /**
   * @brief 解析命令字符串
   * @param cmdStr 命令字符串
   * @return 是否解析成功
   */
  bool parseCommand(const String& cmdStr);

  /**
   * @brief 從字符串中提取整數參數
   * @param str 字符串
   * @param index 參數索引（從0開始）
   * @return 提取的整數值
   */
  int extractParam(const String& str, int index);

  /**
   * @brief 計算字符串中逗號的數量
   * @param str 字符串
   * @return 逗號數量
   */
  int countParams(const String& str);
};

#endif // SERIAL_PROTOCOL_H
