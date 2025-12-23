/**
 * @file SerialProtocol.cpp
 * @brief 串口通訊協議處理器實現
 */

#include "SerialProtocol.h"

SerialProtocol::SerialProtocol() {
  receiveBuffer.reserve(64); // 預分配緩衝區
}

void SerialProtocol::begin() {
  receiveBuffer = "";
}

bool SerialProtocol::processIncoming() {
  // 檢查是否有可用數據
  while (Serial.available() > 0) {
    char c = Serial.read();

    // 檢查是否為結束符
    if (c == '\n' || c == '\r') {
      if (receiveBuffer.length() > 0) {
        // 解析命令
        bool success = parseCommand(receiveBuffer);
        receiveBuffer = ""; // 清空緩衝區
        return success;
      }
    } else if (c == '<') {
      // 命令開始標記，清空緩衝區
      receiveBuffer = "";
    } else if (c == '>') {
      // 命令結束標記，立即解析
      if (receiveBuffer.length() > 0) {
        bool success = parseCommand(receiveBuffer);
        receiveBuffer = "";
        return success;
      }
    } else {
      // 添加字符到緩衝區
      if (receiveBuffer.length() < 63) { // 防止緩衝區溢出
        receiveBuffer += c;
      }
    }
  }

  return false;
}

Command SerialProtocol::getLastCommand() const {
  return lastCommand;
}

void SerialProtocol::sendResponse(bool success, const char* message) {
  Serial.print("{\"status\":\"");
  Serial.print(success ? "ok" : "error");
  Serial.print("\",\"message\":\"");
  Serial.print(message);
  Serial.println("\"}");
}

void SerialProtocol::sendPosition(int panAngle, int tiltAngle) {
  Serial.print("{\"pan\":");
  Serial.print(panAngle);
  Serial.print(",\"tilt\":");
  Serial.print(tiltAngle);
  Serial.println("}");
}

void SerialProtocol::sendStatus(const char* status) {
  Serial.print("{\"status\":\"");
  Serial.print(status);
  Serial.println("\"}");
}

void SerialProtocol::sendTemperature(int panTemp, int tiltTemp) {
  Serial.print("{\"pan_temp\":");
  Serial.print(panTemp);
  Serial.print(",\"tilt_temp\":");
  Serial.print(tiltTemp);
  Serial.println("}");
}

void SerialProtocol::sendVoltage(int panVolt, int tiltVolt) {
  Serial.print("{\"pan_voltage\":");
  Serial.print(panVolt);
  Serial.print(",\"tilt_voltage\":");
  Serial.print(tiltVolt);
  Serial.println("}");
}

void SerialProtocol::sendFullStatus(int pan, int tilt, int panTemp, int tiltTemp, int panVolt, int tiltVolt) {
  Serial.print("{\"pan\":");
  Serial.print(pan);
  Serial.print(",\"tilt\":");
  Serial.print(tilt);
  Serial.print(",\"pan_temp\":");
  Serial.print(panTemp);
  Serial.print(",\"tilt_temp\":");
  Serial.print(tiltTemp);
  Serial.print(",\"pan_voltage\":");
  Serial.print(panVolt);
  Serial.print(",\"tilt_voltage\":");
  Serial.print(tiltVolt);
  Serial.println("}");
}

bool SerialProtocol::parseCommand(const String& cmdStr) {
  // 重置命令
  lastCommand = Command();

  // 提取命令類型
  int colonPos = cmdStr.indexOf(':');
  String cmdType;
  String params;

  if (colonPos != -1) {
    cmdType = cmdStr.substring(0, colonPos);
    params = cmdStr.substring(colonPos + 1);
  } else {
    cmdType = cmdStr;
    params = "";
  }

  // 轉換為大寫
  cmdType.toUpperCase();
  cmdType.trim();

  // 解析命令類型
  if (cmdType == "MOVE" || cmdType == "MOVETO") {
    lastCommand.type = CMD_MOVE_TO;
    if (countParams(params) >= 1) {
      lastCommand.panAngle = extractParam(params, 0);
      lastCommand.tiltAngle = extractParam(params, 1);
      return true;
    }
  }
  else if (cmdType == "MOVER" || cmdType == "MOVEBY") {
    lastCommand.type = CMD_MOVE_BY;
    if (countParams(params) >= 1) {
      lastCommand.panAngle = extractParam(params, 0);
      lastCommand.tiltAngle = extractParam(params, 1);
      return true;
    }
  }
  else if (cmdType == "POS" || cmdType == "GETPOS") {
    lastCommand.type = CMD_GET_POS;
    return true;
  }
  else if (cmdType == "SPEED" || cmdType == "SETSPEED") {
    lastCommand.type = CMD_SET_SPEED;
    lastCommand.speed = extractParam(params, 0);
    return true;
  }
  else if (cmdType == "HOME") {
    lastCommand.type = CMD_HOME;
    return true;
  }
  else if (cmdType == "STOP") {
    lastCommand.type = CMD_STOP;
    return true;
  }
  else if (cmdType == "CAL" || cmdType == "CALIBRATE") {
    lastCommand.type = CMD_CALIBRATE;
    return true;
  }
  else if (cmdType == "READ" || cmdType == "READPOS") {
    lastCommand.type = CMD_READ_POS;
    return true;
  }
  else if (cmdType == "MODE" || cmdType == "SETMODE") {
    lastCommand.type = CMD_SET_MODE;
    lastCommand.mode = extractParam(params, 0);
    return true;
  }
  else if (cmdType == "GETMODE") {
    lastCommand.type = CMD_GET_MODE;
    return true;
  }
  else if (cmdType == "TEMP" || cmdType == "TEMPERATURE") {
    lastCommand.type = CMD_READ_TEMP;
    return true;
  }
  else if (cmdType == "VOLT" || cmdType == "VOLTAGE") {
    lastCommand.type = CMD_READ_VOLTAGE;
    return true;
  }
  else if (cmdType == "STATUS" || cmdType == "INFO") {
    lastCommand.type = CMD_READ_STATUS;
    return true;
  }

  // 未知命令
  return false;
}

int SerialProtocol::extractParam(const String& str, int index) {
  int currentIndex = 0;
  int startPos = 0;

  for (int i = 0; i < str.length(); i++) {
    if (str[i] == ',') {
      if (currentIndex == index) {
        return str.substring(startPos, i).toInt();
      }
      currentIndex++;
      startPos = i + 1;
    }
  }

  // 最後一個參數或唯一參數
  if (currentIndex == index) {
    return str.substring(startPos).toInt();
  }

  return 0;
}

int SerialProtocol::countParams(const String& str) {
  if (str.length() == 0) return 0;

  int count = 1;
  for (int i = 0; i < str.length(); i++) {
    if (str[i] == ',') {
      count++;
    }
  }
  return count;
}
