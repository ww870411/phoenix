"""
Gemini 2.5 Flash 测试脚本（使用新版 google-genai SDK，支持 Google Search Grounding）。
1. 运行 `pip install google-genai` 安装依赖。
2. 推荐通过环境变量 `GOOGLE_GEMINI_API_KEY` 提供密钥；若为空则读取 backend_data/api_key.json。
3. 执行 `python configs/ai_test.py` 进入多轮对话；输入包含“html报告”时会生成 HTML 页面并尝试在浏览器打开。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_KEY_FILE = PROJECT_ROOT / "backend_data" / "api_key.json"
API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY")

REPORTS_DIR = PROJECT_ROOT / "runtime_reports"
HTML_REPORT_INSTRUCTION = (
    "你现在是 HTML 报告生成器，必须严格按照要求输出。"
    "请根据当前多轮对话的全部上下文，直接输出完整的 HTML 文档，包含 <html>、<head>（含<meta charset=\"utf-8\">）和 <body>，"
    "需要包含 ECharts 可视化（使用 https://cdn.jsdelivr.net/npm/echarts/dist/echarts.min.js），至少渲染一张图表，可为折线/柱状/饼图等，"
    "并配套生成图表依赖的数据脚本。可附加内联样式，使整体适合直接在浏览器展示。"
    "报告内容需符合用户在问题中描述的主题与结构，语言为中文。"
    "禁止输出任何解释、提示、免责声明或关于无法打开浏览器/需要复制粘贴的描述，不得包含纯文本说明，"
    "只能返回完整 HTML 源码。若无法遵守，仍需输出符合要求的 HTML。"
)
HTML_TRIGGER_KEYS = ("html报告", "html報告", "html report", "html报告书")

_client: Optional[genai.Client] = None
_model_name: Optional[str] = None
_conversation: List[types.Content] = []

GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())
BASE_CONFIG = types.GenerateContentConfig(tools=[GROUNDING_TOOL])


def load_api_config() -> Tuple[str, str]:
    """
    加载 API Key 与模型名：优先环境变量，否则读取 backend_data/api_key.json。
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


def ensure_client() -> genai.Client:
    global _client, _model_name
    if _client is not None and _model_name:
        return _client

    api_key, model_name = load_api_config()
    _client = genai.Client(api_key=api_key)
    _model_name = model_name
    return _client


def _copy_conversation() -> List[types.Content]:
    return list(_conversation)


def _append_message(role: str, text: str) -> None:
    _conversation.append(types.Content(role=role, parts=[types.Part(text=text)]))


def _extract_text(response: types.GenerateContentResponse) -> str:
    text = getattr(response, "text", "") or ""
    if not text.strip():
        raise RuntimeError(f"模型未返回文本内容：{response}")
    return text.strip()


def wants_html_report(user_text: str) -> bool:
    normalized = user_text.lower().replace(" ", "")
    return any(key in normalized for key in HTML_TRIGGER_KEYS)


def send_message(prompt: str, *, extra_instruction: Optional[str] = None) -> str:
    client = ensure_client()
    contents = _copy_conversation()
    full_prompt = prompt if not extra_instruction else f"{prompt}\n\n{extra_instruction}"
    user_content = types.Content(role="user", parts=[types.Part(text=full_prompt)])
    contents.append(user_content)
    response = client.models.generate_content(
        model=_model_name or "gemini-2.5-flash",
        contents=contents,
        config=BASE_CONFIG,
    )
    answer = _extract_text(response)
    _append_message("user", full_prompt)
    _append_message("model", answer)
    return answer


def save_html_report(html: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REPORTS_DIR / f"gemini_report_{datetime.now():%Y%m%d_%H%M%S}.html"
    file_path.write_text(html, encoding="utf-8")
    return file_path


def open_html_report(file_path: Path) -> None:
    # 依次尝试：os.startfile -> cmd start -> webbrowser，全部失败则提示手动打开
    opened = False
    try:
        os.startfile(file_path)  # type: ignore[attr-defined]
        opened = True
    except Exception:
        pass

    if not opened:
        try:
            subprocess.run(
                ["cmd", "/c", "start", "", str(file_path)],
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW,  # type: ignore[attr-defined]
            )
            opened = True
        except Exception:
            pass

    if not opened:
        try:
            webbrowser.open_new_tab(file_path.as_uri())
            opened = True
        except Exception:
            pass

    if opened:
        print(f"已尝试在浏览器打开：{file_path}")
    else:
        print(f"[警告] 无法自动打开浏览器，请手动打开该文件：{file_path}")


def request_html_report(prompt: str) -> Path:
    html = send_message(prompt, extra_instruction=HTML_REPORT_INSTRUCTION)
    file_path = save_html_report(html)
    open_html_report(file_path)
    return file_path


def main() -> None:
    print("Gemini 2.5 Flash 多轮对话助手（google-genai SDK + Google Search Grounding）。")
    print("输入 exit/quit 结束；若问题包含“html报告”将生成 HTML 页面并尝试打开浏览器。")
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
            if wants_html_report(question):
                report_path = request_html_report(question)
                print(f"AI: 已生成 HTML 报告 → {report_path}")
            else:
                answer = send_message(question)
                print(f"AI: {answer}")
        except Exception as exc:
            print(f"[调用失败] {exc}")


if __name__ == "__main__":
    try:
        ensure_client()
    except Exception as exc:
        print(f"初始化失败：{exc}")
        sys.exit(1)
    main()
