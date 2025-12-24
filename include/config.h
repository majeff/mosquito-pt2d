/**
 * @file config.h
 * @brief 系統配置文件
 * @details 定義硬體引腳、參數和常數
 */

#ifndef CONFIG_H
#define CONFIG_H

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

// 舵機 ID 配置（預設值，啟動時會自動掃描）
#define DEFAULT_PAN_SERVO_ID    1         // Pan 軸舵機 ID（預設值）
#define DEFAULT_TILT_SERVO_ID   2         // Tilt 軸舵機 ID（預設值）
#define AUTO_DETECT_SERVO_ID    true      // 啟動時自動掃描舵機ID

// 自動掃描超時設置
#define SERVO_DETECT_TIMEOUT    500       // 掃描超時（毫秒）
#define SERVO_DETECT_INTERVAL   100       // 掃描嘗試間隔（毫秒）

// ============================================
// 舵機角度範圍
// ============================================
#define SERVO_MAX_ANGLE     270       // 舵機最大角度（0-270）

// Pan 軸 (水平旋轉) - 270度範圍
#define PAN_MIN_ANGLE       0         // Pan 最小角度
#define PAN_MAX_ANGLE       270       // Pan 最大角度
#define PAN_INIT_ANGLE      135       // Pan 初始角度（中心：270/2）

// Tilt 軸 (垂直旋轉) - 180度範圍
#define TILT_MIN_ANGLE      0         // Tilt 最小角度
#define TILT_MAX_ANGLE      180       // Tilt 最大角度
#define TILT_INIT_ANGLE     90        // Tilt 初始角度（中心：180/2）

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
#define FIRMWARE_VERSION    "1.0.0"
#define FIRMWARE_DATE       "2025-12-23"
#define PROJECT_NAME        "Arduino PT2D Controller"

#endif // CONFIG_H
