"""
Gemini 2.5 Flash 聊天机器人测试脚本（使用官方 google-generativeai SDK）。
1. 运行 `pip install google-generativeai` 安装依赖。
2. 推荐通过环境变量 `GOOGLE_GEMINI_API_KEY` 提供密钥；若为空则使用下方的测试密钥。
3. 运行 `python configs/ai_test.py`，输入问题并查看回复，输入 exit/quit 结束。
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

try:
    import google.generativeai as genai
    from google.api_core.exceptions import GoogleAPIError
except ImportError:
    genai = None  # type: ignore
    GoogleAPIError = Exception

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_KEY_FILE = PROJECT_ROOT / "backend_data" / "api_key.json"
API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY")
_model: Optional[Any] = None


def load_api_config() -> Tuple[str, str]:
    """
    加载 API Key 与模型名：优先使用环境变量，否则读取 backend_data/api_key.json。
    """
    if API_KEY:
        model_name = os.environ.get("GOOGLE_GEMINI_MODEL", "").strip()
        return API_KEY, model_name or "gemini-2.5-flash"

    if API_KEY_FILE.exists():
        try:
            data = json.loads(API_KEY_FILE.read_text(encoding="utf-8"))
            key = data.get("gemini_api_key", "").strip()
            model_name = data.get("gemini_model", "").strip() or "gemini-2.5-flash"
            if key:
                return key, model_name
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"无法解析 {API_KEY_FILE}: {exc}") from exc

    raise RuntimeError("未检测到 API Key，请设置环境变量或在 backend_data/api_key.json 中配置。")


def ensure_model() -> Any:
    """
    初始化或返回缓存的 GenerativeModel 实例。
    """
    if genai is None:
        raise RuntimeError("未检测到 google-generativeai，请运行 pip install google-generativeai")

    global _model
    if _model is not None:
        return _model

    api_key, model_name = load_api_config()

    genai.configure(api_key=api_key)
    _model = genai.GenerativeModel(model_name)
    return _model


def request_gemini(prompt: str) -> str:
    """
    调用 Gemini 2.5 Flash 接口并返回文本回复。
    """
    model = ensure_model()
    response = model.generate_content(prompt)

    if not getattr(response, "text", "").strip():
        raise RuntimeError(f"模型未返回文本内容：{response}")

    return response.text.strip()


def main() -> None:
    print("Gemini 2.5 Flash 测试对话（genai SDK 版本），输入 exit/quit 结束。")
    while True:
        try:
            question = input("你: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n手动中断，程序退出。")
            return

        if not question:
            continue

        if question.lower() in {"exit", "quit"}:
            print("程序结束。")
            break

        try:
            answer = request_gemini(question)
        except GoogleAPIError as http_err:
            print(f"[Google API 错误] {http_err}")
        except Exception as exc:  # 捕获 SDK 及通用异常
            print(f"[调用失败] {exc}")
        else:
            print(f"AI: {answer}")


if __name__ == "__main__":
    if genai is None:
        print("请先安装 google-generativeai，示例：pip install google-generativeai")
        sys.exit(1)
    main()
