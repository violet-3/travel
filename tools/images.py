"""图片策略 · 三层降级: 本地 > 百度 > Picsum"""

import os
from config import default_config


def get_image(w: int, h: int, name: str, city: str = "", category: str = "scenic") -> str:
    """
    获取景点/美食图片 URL

    优先级:
    1. 本地图片: static/photos/{城市}/{名称}.jpg
    2. Picsum 占位 (用 city+name+category 做 seed)
    """
    # Level 1: 本地图片
    local_dir = ""                                           # ← FIX: 不再使用 access_key 充当目录
    img_cfg = getattr(default_config, 'image', None)         # ← FIX: 优先走 image 配置
    if img_cfg and img_cfg.local_photo_dir:
        local_dir = img_cfg.local_photo_dir

    if local_dir and os.path.isdir(local_dir):
        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            path = os.path.join(local_dir, city, name + ext)
            if os.path.isfile(path):
                return f"/static/photos/{city}/{name}{ext}"
            path = os.path.join(local_dir, name + ext)
            if os.path.isfile(path):
                return f"/static/photos/{name}{ext}"

    # Level 2: Picsum
    seed = f"{city}-{name}-{category}".replace(" ", "-").replace("#", "").lower()[:50]
    return f"https://picsum.photos/seed/{seed}/{w}/{h}"