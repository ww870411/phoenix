"""
API Key 简易加解密工具。

约定：
- 加密：在明文第 5 个字符（1-based）之后插入 "ww"；
- 解密：若密文第 6、7 个字符为 "ww"，则删除。
"""

from __future__ import annotations

from typing import Optional

_INSERT_TOKEN = "ww"
_INSERT_POS = 5  # 1-based 第 5 个字符之后，即 0-based index 5


def encrypt_api_key(plaintext: Optional[str]) -> str:
    """
    在明文第 5 个字符后插入固定 token。
    若长度不足 5，则直接拼接在末尾。
    """

    if not plaintext:
        return ""
    text = str(plaintext)
    if len(text) <= _INSERT_POS:
        return f"{text}{_INSERT_TOKEN}"
    return f"{text[:_INSERT_POS]}{_INSERT_TOKEN}{text[_INSERT_POS:]}"


def decrypt_api_key(ciphertext: Optional[str]) -> str:
    """
    检查密文第 6、7 位是否为固定 token，若是则移除。
    兼容处理长度不足 5 时 token 位于末尾的情况。
    """

    if not ciphertext:
        return ""
    text = str(ciphertext)
    
    # Case 1: 原文长度 >= 5，token 插入在 index 5
    token_at_5 = _INSERT_POS + len(_INSERT_TOKEN)
    if len(text) >= token_at_5 and text[_INSERT_POS:token_at_5] == _INSERT_TOKEN:
        return f"{text[:_INSERT_POS]}{text[token_at_5:]}"
    
    # Case 2: 原文长度 < 5，token 拼接在末尾
    # 密文长度应 < 5 + 2 = 7
    if len(text) < token_at_5 and text.endswith(_INSERT_TOKEN):
        return text[:-len(_INSERT_TOKEN)]
        
    return text
