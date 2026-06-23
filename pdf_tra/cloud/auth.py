from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import jwt

from pdf_tra.cloud.settings import CloudSettings


class AuthError(Exception):
    pass


def exchange_wechat_code(settings: CloudSettings, code: str) -> str:
    if settings.dev_mode:
        return "dev-openid"

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.wechat_app_id,
        "secret": settings.wechat_app_secret,
        "js_code": code,
        "grant_type": "authorization_code",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("errcode"):
        raise AuthError(data.get("errmsg", "微信登录失败"))
    openid = data.get("openid")
    if not openid:
        raise AuthError("微信未返回 openid")
    return str(openid)


def create_token(settings: CloudSettings, openid: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    payload = {"sub": openid, "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_token(settings: CloudSettings, token: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AuthError("登录已失效，请重新打开小程序") from exc
    openid = payload.get("sub")
    if not openid:
        raise AuthError("无效令牌")
    return str(openid)


def mask_openid(openid: str) -> str:
    if len(openid) <= 8:
        return "****"
    return f"{openid[:4]}****{openid[-4:]}"
