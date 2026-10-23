"""高德 Web 服务公共工具 · 数字签名

签名算法 (高德数字签名文档):
  1. 请求参数（包含 key）按参数名升序排列
  2. 使用原始参数值拼成 key=value&key=value...
  3. 末尾拼接 Web 服务签名密钥，整体按 UTF-8 取 MD5
  4. 发请求时再对参数做 URL 编码
"""

import hashlib


def amap_sign(params: dict, secret: str) -> str:
    """计算高徽数字签名，secret 为空则返回空串"""
    if not secret:
        return ""
    items = sorted((str(k), str(v)) for k, v in params.items())
    raw = "&".join(f"{k}={v}" for k, v in items) + secret
    return hashlib.md5(raw.encode()).hexdigest()


def with_sig(params: dict, key: str, secret: str) -> dict:
    """补全 key / sig，返回可直接用于请求的参数"""
    p = {**params, "key": key}
    sig = amap_sign(p, secret)
    if sig:
        p["sig"] = sig
    return p
