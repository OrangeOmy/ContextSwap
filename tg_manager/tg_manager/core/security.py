"""
安全与鉴权（MVP 版）。

当前策略：
- 对外 HTTP API 使用静态 token 鉴权。
- 约定客户端通过 `Authorization: Bearer <token>` 传递。
"""

from __future__ import annotations


class AuthError(Exception):
    """鉴权失败。"""


def parse_bearer_token(authorization_header: str | None) -> str | None:
    """从 Authorization 头解析 Bearer token。

返回：
    - 解析成功：token 字符串
    - 头不存在或格式不匹配：None
    """

    if not authorization_header:
        return None
    raw = authorization_header.strip()
    if not raw:
        return None
    prefix = "Bearer "
    if not raw.startswith(prefix):
        return None
    token = raw[len(prefix) :].strip()
    return token or None


def verify_bearer_token(authorization_header: str | None, expected_token: str) -> None:
    """校验请求是否携带正确的 Bearer token。

异常：
    AuthError：当 token 缺失或不匹配时抛出。
    """

    token = parse_bearer_token(authorization_header)
    if token is None:
        raise AuthError("缺少或不合法的 Authorization 头（需要 Bearer token）")
    if token != expected_token:
        raise AuthError("鉴权失败：token 不匹配")

