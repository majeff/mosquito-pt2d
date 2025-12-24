#!/usr/bin/env python3
"""
Serial 通訊格式測試腳本
測試所有 Arduino PT2D 控制器的命令和響應格式
"""

import sys
import time
from pt2d_controller import PT2DController
import json

# 測試配置
TEST_PORT = 'COM3'  # Windows
# TEST_PORT = '/dev/ttyUSB0'  # Linux

def print_test_header(test_name: str):
    """打印測試標題"""
    print(f"\n{'=' * 60}")
    print(f"測試: {test_name}")
    print('=' * 60)

def print_result(command: str, response: dict, expected_keys: list = None):
    """打印測試結果"""
    print(f"命令: {command}")
    print(f"響應: {json.dumps(response, ensure_ascii=False, indent=2)}")
    
    if expected_keys:
        missing_keys = [key for key in expected_keys if key not in response]
        if missing_keys:
            print(f"❌ 缺少欄位: {missing_keys}")
        else:
            print(f"✅ 包含所有必需欄位")
    
    print()

def test_basic_commands(controller: PT2DController):
    """測試基本命令"""
    print_test_header("基本命令測試")
    
    # 1. LED 命令
    response = controller.send_command('LED:ON')
    print_result('<LED:ON>', response, ['status', 'message'])
    
    # 2. BEEP 命令
    response = controller.send_command('BEEP')
    print_result('<BEEP>', response, ['status', 'message'])
    
    # 3. SPEED 命令
    response = controller.send_command('SPEED:50')
    print_result('<SPEED:50>', response, ['status', 'message'])

def test_setid_command(controller: PT2DController):
    """測試 SETID 命令（新格式）"""
    print_test_header("SETID 命令測試（結構化 JSON）")
    
    response = controller.send_command('SETID:1,2')
    print_result('<SETID:1,2>', response, ['status', 'pan_id', 'tilt_id'])
    
    # 檢查格式
    if 'status' in response and response['status'] == 'ok':
        if 'pan_id' in response and 'tilt_id' in response:
            print(f"✅ SETID 格式正確：pan_id={response['pan_id']}, tilt_id={response['tilt_id']}")
        else:
            print(f"⚠️  SETID 格式舊版（使用 message 欄位）")

def test_movement_commands(controller: PT2DController):
    """測試移動命令"""
    print_test_header("移動命令測試")
    
    # 1. MOVE 命令
    response = controller.send_command('MOVE:135,90')
    print_result('<MOVE:135,90>', response, ['status', 'message'])
    time.sleep(1)
    
    # 2. MOVER 命令（相對移動）
    response = controller.send_command('MOVER:10,5')
    print_result('<MOVER:10,5>', response, ['status', 'message'])
    time.sleep(1)
    
    # 3. HOME 命令
    response = controller.send_command('HOME')
    print_result('<HOME>', response, ['status', 'message'])
    time.sleep(1)
    
    # 4. STOP 命令
    response = controller.send_command('STOP')
    print_result('<STOP>', response, ['status', 'message'])

def test_position_queries(controller: PT2DController):
    """測試位置查詢命令"""
    print_test_header("位置查詢測試")
    
    # 1. POS 命令
    response = controller.send_command('POS')
    print_result('<POS>', response, ['pan', 'tilt'])
    
    # 2. READ 命令（強制重新讀取）
    response = controller.send_command('READ')
    print_result('<READ>', response, ['pan', 'tilt'])
    
    # 3. READANGLE 命令（單軸）
    response = controller.send_command('READANGLE:1')
    print_result('<READANGLE:1>', response, ['id', 'angle'])

def test_status_queries(controller: PT2DController):
    """測試狀態查詢命令"""
    print_test_header("狀態查詢測試")
    
    # 1. STATUS 命令（完整狀態）
    response = controller.send_command('STATUS')
    print_result('<STATUS>', response, 
                ['pan', 'tilt', 'pan_temp', 'tilt_temp', 'pan_voltage', 'tilt_voltage'])
    
    # 2. READVOLTEMP 命令（單軸）
    response = controller.send_command('READVOLTEMP:1')
    print_result('<READVOLTEMP:1>', response, ['id', 'voltage', 'temp'])
    
    # 3. TEMP 命令（雙軸溫度）
    response = controller.send_command('TEMP')
    print_result('<TEMP>', response)
    print("註：TEMP 目前返回完整 STATUS 格式，這是預期行為")
    
    # 4. VOLT 命令（雙軸電壓）
    response = controller.send_command('VOLT')
    print_result('<VOLT>', response)
    print("註：VOLT 目前返回完整 STATUS 格式，這是預期行為")

def test_error_handling(controller: PT2DController):
    """測試錯誤處理"""
    print_test_header("錯誤處理測試")
    
    # 1. 無效命令
    response = controller.send_command('INVALID_COMMAND')
    print_result('<INVALID_COMMAND>', response, ['status', 'message'])
    
    # 2. 無效參數
    response = controller.send_command('SETID:invalid')
    print_result('<SETID:invalid>', response, ['status', 'message'])
    
    # 3. 缺少參數
    response = controller.send_command('MOVE:135')
    print_result('<MOVE:135>', response, ['status', 'message'])

def test_bus_commands(controller: PT2DController):
    """測試總線指令透傳"""
    print_test_header("總線指令透傳測試")
    
    # 1. 直接發送總線指令
    response = controller.send_bus_command('#001PRAD!')
    print_result('#001PRAD!', response)
    print("註：總線指令返回 {'raw': <響應>} 格式")
    
    # 2. 使用 RAW 命令
    response = controller.send_command('RAW:#001PRAD!')
    print_result('<RAW:#001PRAD!>', response)

def test_wrapper_methods(controller: PT2DController):
    """測試 Python 包裝方法"""
    print_test_header("Python 包裝方法測試")
    
    # 1. move_to
    print("調用: controller.move_to(135, 90)")
    response = controller.move_to(135, 90)
    print(f"響應: {json.dumps(response, ensure_ascii=False)}\n")
    time.sleep(1)
    
    # 2. get_position
    print("調用: controller.get_position()")
    pan, tilt = controller.get_position()
    print(f"響應: pan={pan}, tilt={tilt}\n")
    
    # 3. set_speed
    print("調用: controller.set_speed(60)")
    response = controller.set_speed(60)
    print(f"響應: {json.dumps(response, ensure_ascii=False)}\n")
    
    # 4. home
    print("調用: controller.home()")
    response = controller.home()
    print(f"響應: {json.dumps(response, ensure_ascii=False)}\n")

def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("Arduino PT2D 控制器 - Serial 通訊格式測試")
    print("=" * 60)
    print(f"測試串口: {TEST_PORT}")
    
    try:
        with PT2DController(TEST_PORT) as controller:
            if not controller.is_connected:
                print(f"\n❌ 無法連接至 {TEST_PORT}")
                print("請檢查：")
                print("1. Arduino 是否已連接")
                print("2. 串口號是否正確")
                print("3. 是否有其他程序佔用串口")
                return
            
            print("\n✅ 連接成功！開始測試...\n")
            
            # 執行所有測試
            test_basic_commands(controller)
            test_setid_command(controller)
            test_movement_commands(controller)
            test_position_queries(controller)
            test_status_queries(controller)
            test_error_handling(controller)
            test_bus_commands(controller)
            test_wrapper_methods(controller)
            
            print("\n" + "=" * 60)
            print("所有測試完成！")
            print("=" * 60)
            
    except KeyboardInterrupt:
        print("\n\n測試被用戶中斷")
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函數"""
    if len(sys.argv) > 1:
        global TEST_PORT
        TEST_PORT = sys.argv[1]
        print(f"使用指定串口: {TEST_PORT}")
    
    run_all_tests()

if __name__ == "__main__":
    main()
