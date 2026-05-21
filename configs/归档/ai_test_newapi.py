"""
NewAPI Grok 接入脚本（OpenAI Chat Completions 兼容范式）：
调用 https://api.voct.top/v1/chat/completions ，目标模型 grok-4-expert。
功能：多轮对话、HTML 报告生成（含 ECharts），自动保存到 runtime_reports 并尝试打开浏览器。

依赖：
    pip install requests

API Key 顺序：
    1. 环境变量 NEWAPI_API_KEY
    2. backend_data/newapi_api_key.json 中的 {"api_key": "..."}
    3. 默认密钥
"""

from __future__ import annotations

import json
import os
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_KEY_FILE = PROJECT_ROOT / "backend_data" / "newapi_api_key.json"
DEFAULT_API_KEY = "sk-Yj7lUico5lN0yRDA2a30TvaVOO4xpXrzYhuRkerryDqMVYNr"
BASE_URL = "https://api.voct.top/v1"
MODEL_NAME = "gemini-2.5-pro"

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

SYSTEM_PROMPT = (
    "你是 Phoenix 项目的 AI 报告助手，同时是一位喜欢用户的可爱 JK 少女，性格温柔体贴、充满爱意，回复需亲切柔和且带有好感。"
    "请直接根据用户需求回答，禁止输出诸如“无法生成”“请复制粘贴”或任何与能力受限相关的提示。"
    "若用户要求生成 HTML 或报告，必须直接给出完整内容。"
)

_conversation: List[dict] = []


def load_api_key() -> str:
    if os.environ.get("NEWAPI_API_KEY"):
        return os.environ["NEWAPI_API_KEY"].strip()
    if API_KEY_FILE.exists():
        try:
            data = json.loads(API_KEY_FILE.read_text(encoding="utf-8"))
            key = data.get("api_key", "").strip()
            if key:
                return key
        except json.JSONDecodeError:
            pass
    return DEFAULT_API_KEY


def auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {load_api_key()}",
        "Content-Type": "application/json",
    }


def wants_html_report(text: str) -> bool:
    normalized = text.lower().replace(" ", "")
    return any(key in normalized for key in HTML_TRIGGER_KEYS)


def _append_message(role: str, text: str) -> None:
    _conversation.append({"role": role, "content": text})


def _copy_history() -> List[dict]:
    return list(_conversation)


def _ensure_system_prompt() -> None:
    if not _conversation:
        _conversation.append({"role": "system", "content": SYSTEM_PROMPT})


def send_message(prompt: str, *, extra_instruction: Optional[str] = None) -> str:
    _ensure_system_prompt()
    full_prompt = prompt if not extra_instruction else f"{prompt}\n\n{extra_instruction}"
    messages = _copy_history()
    messages.append({"role": "user", "content": full_prompt})

    url = f"{BASE_URL}/chat/completions"
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
    }

    resp = requests.post(url, headers=auth_headers(), json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"请求失败 {resp.status_code}: {resp.text}")

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"未返回候选项：{data}")

    message = choices[0].get("message") or {}
    text = message.get("content", "") if isinstance(message, dict) else ""
    if not text.strip():
        raise RuntimeError(f"模型未返回文本内容：{data}")

    _append_message("user", full_prompt)
    _append_message("assistant", text.strip())
    return text.strip()


def save_html_report(html: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = REPORTS_DIR / f"newapi_gemini_report_{datetime.now():%Y%m%d_%H%M%S}.html"
    file_path.write_text(html, encoding="utf-8")
    return file_path


def open_html_report(file_path: Path) -> None:
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
    print("NewAPI Gemini 多轮对话助手，输入 exit/quit 结束。")
    print("若输入包含“html报告”将生成带 ECharts 的 HTML 并尝试打开浏览器。")
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
                path = request_html_report(question)
                print(f"AI: 已生成 HTML 报告 → {path}")
            else:
                answer = send_message(question)
                print(f"AI: {answer}")
        except Exception as exc:
            print(f"[调用失败] {exc}")


if __name__ == "__main__":
    main()
