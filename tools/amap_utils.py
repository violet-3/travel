"""高德 Web 服务公共工具 · 数字签名

签名算法 (官方文档 https://lbs.amap.com/api/webservice/guide/tools/validate):
  1. 请求参数按 key 升序排序
  2. 参数值先做 URL 编码 (UTF-8)，再拼成 key=value&key=value...
  3. 末尾拼接私钥，整体取 MD5
"""

import hashlib
from urllib.parse import quote


def amap_sign(params: dict, secret: str) -> str:
    """计算高徽数字签名，secret 为空则返回空串"""
    if not secret:
        return ""
    items = sorted((k, quote(str(v), safe="")) for k, v in params.items())
    raw = "&".join(f"{k}={v}" for k, v in items) + secret
    return hashlib.md5(raw.encode()).hexdigest()


def with_sig(params: dict, key: str, secret: str) -> dict:
    """补全 key / sig，返回可直接用于请求的参数"""
    p = {**params, "key": key}
    sig = amap_sign(p, secret)
    if sig:
        p["sig"] = sig
    return p
