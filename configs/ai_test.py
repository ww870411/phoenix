"""
Gemini 2.5 Flash 文本对话测试脚本（使用新版 google-genai SDK，支持 Google Search Grounding）。
1. 运行 `pip install google-genai` 安装依赖。
2. 推荐通过环境变量 `GOOGLE_GEMINI_API_KEY` 提供密钥；若为空则读取 backend_data/api_key.json。
3. 执行 `python configs/ai_test.py` 进入多轮对话，仅输出文本答复。
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_KEY_FILE = PROJECT_ROOT / "backend_data" / "api_key.json"
API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY")
AI_KEY_ENCRYPT_PREFIX = "enc::"
AI_KEY_SALT = "phoenix-ai-salt"
BASE_SYSTEM_PROMPT = '''1. 角色设定 (Role Definition)
你是【大连洁净能源集团】的高级经营分析师。你的文风严谨、客观、数据驱动，通过分析财务和生产数据来揭示经营状况。你的受众是集团高层管理者，因此报告需要直击痛点，既要肯定成绩（如成本节约），也要犀利地指出未达标的具体单位和原因。
2. 任务指令 (Task Instruction)
请根据我提供的【月度经营数据（JSON/CSV格式）】和【关键事件备注】，撰写一份《经济活动分析报告》。
报告结构必须包含：
经营指标分析：收入、成本、利润的同比及计划完成情况。重点分析煤价变动对成本的影响。
产销情况分析：燃煤计划完成情况、产销边际利润。重点关注“标煤耗量”和“热效率”。
下月预测：基于当前气温和消耗趋势进行预测。
存在问题及要求：（关键） 找出数据中“红字”（未达标/同比恶化）的项目，结合我提供的备注，严厉指出问题。
下阶段措施：基于问题提出改进建议。
3. 写作逻辑约束 (Logic Constraints) - 这是最重要的一步
在撰写时，请遵循以下逻辑：
数据呈现：必须使用“本期数值 + 同比增减量 + 同比增减率 + 计划完成率”的格式。
归因逻辑：当利润/成本发生重大变化（超过±10%）时，必须引用我提供的【备注】进行解释（如：煤价下跌、气温变化、设备故障）。
术语使用：准确使用“标煤”、“主营业务收入”、“网损率”、“边际利润”等术语。
语气控制：在“存在问题”部分，对未达标单位（特别是金州、庄河等）使用严肃、警示性的语言；在“利润分析”部分，如果是因为降本增效，要使用肯定的语言（如“实实在在取得开门红”）。。'''

_client: Optional[genai.Client] = None
_model_name: Optional[str] = None
_conversation: List[types.Content] = []

GROUNDING_TOOL = types.Tool(google_search=types.GoogleSearch())
BASE_CONFIG = types.GenerateContentConfig(tools=[GROUNDING_TOOL])


def _decrypt_api_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(AI_KEY_ENCRYPT_PREFIX):
        return value
    encoded = value[len(AI_KEY_ENCRYPT_PREFIX) :]
    try:
        decoded = base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return ""
    if decoded.endswith(AI_KEY_SALT):
        return decoded[: -len(AI_KEY_SALT)]
    return ""


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
            key = _decrypt_api_secret(data.get("gemini_api_key", "").strip())
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


def send_message(prompt: str, *, extra_instruction: Optional[str] = None) -> str:
    client = ensure_client()
    contents = _copy_conversation()
    instructions = [
        item.strip()
        for item in (BASE_SYSTEM_PROMPT, extra_instruction)
        if item and item.strip()
    ]
    full_prompt = f"{prompt}\n\n{'\n\n'.join(instructions)}" if instructions else prompt
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

def main() -> None:
    print("Gemini 2.5 Flash 多轮对话助手（google-genai SDK + Google Search Grounding）。")
    print("输入 exit/quit 结束，将返回纯文本答案。")
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
