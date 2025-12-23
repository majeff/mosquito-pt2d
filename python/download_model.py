"""
蚊子檢測模型下載腳本
此腳本可以幫助您從指定來源下載蚊子檢測模型
"""

import os
import requests
import urllib.request
from pathlib import Path


def create_models_directory():
    """創建models目錄（如果不存在）"""
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    print(f"確保 {models_dir} 目錄存在")


def download_model_from_url(url, filename):
    """從指定URL下載模型文件"""
    models_path = Path("models") / filename
    print(f"正在下載 {filename} 到 {models_path}...")

    try:
        # 使用urllib下載文件
        urllib.request.urlretrieve(url, models_path)
        print(f"✓ 成功下載 {filename}")
        return True
    except Exception as e:
        print(f"✗ 下載失敗: {e}")
        return False


def download_from_roboflow(api_key, project_info, output_path):
    """
    從Roboflow下載模型
    需要先註冊Roboflow並獲取API密鑰
    """
    print("提示: 要從Roboflow下載模型，您需要:")
    print("1. 註冊Roboflow帳戶 (https://roboflow.com)")
    print("2. 找到一個蚊子檢測項目")
    print("3. 獲取API密鑰")
    print("4. 將項目設為可導出YOLO格式")

    # 這是一個示例URL格式，實際需要根據具體項目調整
    if api_key and project_info:
        download_url = f"https://api.roboflow.com/{project_info}?api_key={api_key}&format=yolov8"
        return download_model_from_url(download_url, output_path)
    else:
        print("缺少API密鑰或項目信息，跳過Roboflow下載")
        return False


def search_pretrained_models():
    """搜索可用的預訓練模型"""
    print("\n可用的蚊子檢測模型下載來源:")
    print("1. Roboflow Universe - https://universe.roboflow.com/")
    print("   搜尋: mosquito detection")
    print("2. Kaggle Datasets - https://www.kaggle.com/datasets")
    print("   搜尋: mosquito detection dataset")
    print("3. GitHub - https://github.com/search")
    print("   搜尋: mosquito detection yolo")

    print("\n或者您可以嘗試通用的YOLOv8預訓練模型:")
    print("此模型未專門訓練用於蚊子檢測，但可以用作起點:")
    print("yolov8n.pt - 小型通用模型 (約6MB)")


def download_yolo_base_model():
    """下載基礎YOLOv8模型"""
    print("\n提示: 首次運行 mosquito_detector.py 時")
    print("系統會自動下載YOLOv8n預訓練模型 (約6MB)")
    print("如果您想手動下載，可以訪問:")
    print("https://github.com/ultralytics/assets/releases/")
    print("查找 yolov8n.pt 文件")
    return False  # 不自動下載，因為需要用戶手動操作


def main():
    print("=== 蚊子檢測模型下載助手 ===\n")

    # 創建models目錄
    create_models_directory()

    print("\n方法1: 手動下載模型")
    print("- 訪問 Roboflow Universe (https://universe.roboflow.com/)")
    print("- 搜尋 '" \
    "'")
    print("- 選擇一個項目並導出 YOLOv8 格式")
    print("- 將下載的模型文件複製到 models/ 目錄")

    print("\n方法2: 使用API下載 (需要註冊)")
    print("如果您已有Roboflow API密鑰，請在下面輸入:")

    # 搜索可用模型
    search_pretrained_models()

    print("\n方法3: 首次運行自動下載")
    print("直接運行 mosquito_detector.py 將自動下載YOLOv8n模型")
    print("運行命令: python mosquito_detector.py")

    print("\n模型文件應放置在: models/ 目錄下")
    print("例如: models/mosquito_yolov8n.pt")

    print("\n配置文件中的模型路徑設置:")
    print("在 mosquito_tracker.py 中設置:")
    print("AI_MODEL_PATH = 'models/mosquito_yolov8n.pt'")


if __name__ == "__main__":
    main()