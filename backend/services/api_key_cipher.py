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
    """

    if not ciphertext:
        return ""
    text = str(ciphertext)
    token_end = _INSERT_POS + len(_INSERT_TOKEN)
    if len(text) >= token_end and text[_INSERT_POS:token_end] == _INSERT_TOKEN:
        return f"{text[:_INSERT_POS]}{text[token_end:]}"
    return text
