/*
 * Copyright 2025 Arduino PT2D Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/**
 * @file config.h
 * @brief 系統配置文件
 * @details 定義硬體引腳、參數和常數
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================
// 傳感器接口配置 (DJ0-DJ5)
// ============================================
// ZL-KPZ 控制板提供 6 組傳感器接口（對應 Arduino 引腳 D7, D3, D5, D6, D9, D8）
#define SENSOR_PIN_1        7         // DJ0 - 傳感器 1 信號引腳
#define SENSOR_PIN_2        3         // DJ1 - 傳感器 2 信號引腳
#define SENSOR_PIN_3        5         // DJ2 - 傳感器 3 信號引腳
#define SENSOR_PIN_4        6         // DJ3 - 傳感器 4 信號引腳
#define SENSOR_PIN_5        9         // DJ4 - 傳感器 5 信號引腳
#define SENSOR_PIN_6        8         // DJ5 - 傳感器 6 信號引腳

// ============================================
// 基本控制引腳
// ============================================
#define LED_PIN             13        // LED 指示燈（Arduino 內建 LED）
#define BEEP_PIN            4         // 蜂鳴器引腳
#define IR_PIN              2         // 紅外接收引腳
#define KEY1_PIN            A1        // 按鍵 1
#define KEY2_PIN            A2        // 按鍵 2

// ============================================
// PS 遊戲手把接口 (PS口10-13)
// ============================================
#define PS_CLK_PIN          11        // psCLK - PS口10
#define PS_ATT_PIN          A3        // psATT - PS口11
#define PS_CMD_PIN          A0        // psCMD - PS口12
#define PS_DAT_PIN          12        // psDAT - PS口13

// ============================================
// 舵機信號接口 (SSA/SSD)
// ============================================
// SSA - 舵機 A 信號線
#define SSA1_PIN            A6        // 舵機組 1-A
#define SSA2_PIN            A0        // 舵機組 2-A
#define SSA3_PIN            A2        // 舵機組 3-A
#define SSA4_PIN            A1        // 舵機組 4-A
#define SSA5_PIN            A3        // 舵機組 5-A
#define SSA6_PIN            A4        // 舵機組 6-A

// SSD - 舵機 D 信號線
#define SSD1_PIN            A7        // 舵機組 1-D
#define SSD2_PIN            A3        // 舵機組 2-D
#define SSD3_PIN            A1        // 舵機組 3-D
#define SSD4_PIN            2         // 舵機組 4-D
#define SSD5_PIN            A0        // 舵機組 5-D
#define SSD6_PIN            A5        // 舵機組 6-D

// ============================================
// 串口引腳
// ============================================
#define TXD1_PIN            1         // TX (Serial)
#define RXD1_PIN            0         // RX (Serial)

// 雷射控制配置
#define LASER_PIN           SENSOR_PIN_4  // 雷射接在傳感器 4 / DJ3 (Pin D6)

// ============================================
// 串口配置
// ============================================
#define SERIAL_BAUDRATE     115200    // 上位機串口波特率
#define SERVO_BAUDRATE      115200    // 舵機總線波特率（常見：9600/115200）

// ============================================
// 總線舵機配置
// ============================================
// 使用 Serial1 連接舵機總線（Arduino Mega）
// 如果是 Uno/Nano，需使用 SoftwareSerial
#if defined(__AVR_ATmega2560__)
  #define SERVO_SERIAL      Serial1   // Mega: 使用 Serial1 (TX1=18, RX1=19)
#else
  #include <SoftwareSerial.h>
  extern SoftwareSerial ServoSerial;
  #define SERVO_SERIAL      ServoSerial  // Uno/Nano: 軟串口
  #define SERVO_TX_PIN      10           // 舵機 TX 引腳
  #define SERVO_RX_PIN      11           // 舵機 RX 引腳
#endif

// 舵機 ID 配置（廢棄預設值，啟動時必須自動掃描）
#define AUTO_DETECT_SERVO_ID    true      // 啟動時強制自動掃描舵機ID（不使用預設值）

// 自動掃描超時設置
#define SERVO_DETECT_TIMEOUT    500       // 掃描超時（毫秒）
#define SERVO_DETECT_INTERVAL   100       // 掃描嘗試間隔（毫秒）
#define SERVO_DETECT_RETRIES    3         // 掃描重試次數（每個舵機）
#define SERVO_STARTUP_DELAY     1000      // 啟動等待延遲（毫秒，等待舵機初始化）
#define SERVO_DETECT_RETRY_DELAY 500      // 掃描重試延遲（毫秒）

// ============================================
// 舵機角度範圍
// ============================================
#define SERVO_MAX_ANGLE     270       // 舵機最大角度（0-270）

// Pan 軸 (水平旋轉) - 270度範圍
#define PAN_MIN_ANGLE       0         // Pan 最小角度
#define PAN_MAX_ANGLE       270       // Pan 最大角度
#define PAN_INIT_ANGLE      135       // Pan 初始角度（中心：270/2）

// Tilt 軸 (垂直旋轉) - 150度安全範圍 (15-165度，留有15度安全邊距)
#define TILT_MIN_ANGLE      15        // Tilt 最小角度（安全限制）
#define TILT_MAX_ANGLE      165       // Tilt 最大角度（安全限制）
#define TILT_INIT_ANGLE     90        // Tilt 初始角度（中心：(15+165)/2）

// ============================================
// 運動參數
// ============================================
#define DEFAULT_SPEED       50        // 預設移動速度 (1-100)
#define MIN_SPEED           1         // 最小速度
#define MAX_SPEED           100       // 最大速度

#define SMOOTH_MOVE_STEP    1         // 平滑移動步進 (度)
#define UPDATE_INTERVAL     20        // 更新間隔 (毫秒)

// ============================================
// 自動掃描模式參數
// ============================================
#define SCAN_TILT_ANGLE     20        // 掃描時垂直固定角度
#define SCAN_CENTER_PAN     135       // 掃描中心位置 (Pan 軸)
#define SCAN_RANGE          120       // 掃描範圍（度）
#define SCAN_SPEED          20        // 掃描速度（慢速）
#define SCAN_UPDATE_INTERVAL 100      // 掃描更新間隔（毫秒）

// ============================================
// 串口通訊協議
// ============================================
#define CMD_START_CHAR      '<'       // 命令開始字符
#define CMD_END_CHAR        '>'       // 命令結束字符
#define CMD_SEPARATOR       ','       // 參數分隔符
#define CMD_MAX_LENGTH      64        // 命令最大長度

// ============================================
// 調試選項
// ============================================
#define DEBUG_MODE          true      // 是否啟用調試模式
#define DEBUG_SERIAL        Serial    // 調試輸出串口

// 調試宏
#if DEBUG_MODE
  #define DEBUG_PRINT(x)    DEBUG_SERIAL.print(x)
  #define DEBUG_PRINTLN(x)  DEBUG_SERIAL.println(x)
#else
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
#endif

// ============================================
// 版本信息
// ============================================
#define FIRMWARE_VERSION    "2.4.0"
#define FIRMWARE_DATE       "2025-12-28"
#define PROJECT_NAME        "Arduino PT2D Controller"

#endif // CONFIG_H
