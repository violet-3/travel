"""
图片抓取 · Playwright 模拟浏览器
目标: 小红书/百度图片搜索 → 下载景点/美食图片到本地

安装: pip install playwright && playwright install chromium
"""

import os
import asyncio
from pathlib import Path

PHOTO_DIR = Path(__file__).parent.parent / "static" / "photos"


async def search_baidu_images(query: str, count: int = 5) -> list[str]:
    """百度图片搜索 (稳定，反爬弱)"""
    from playwright.async_api import async_playwright

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"https://image.baidu.com/search?word={query}&tn=baiduimage", timeout=15000)
        await page.wait_for_selector("img.main_img", timeout=10000)
        # 滚动加载更多
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(0.5)
        imgs = await page.query_selector_all("img.main_img")
        for img in imgs[:count]:
            src = await img.get_attribute("src")
            if src and src.startswith("http"):
                results.append(src)
        await browser.close()
    return results


async def search_xiaohongshu_images(query: str, count: int = 5) -> list[str]:
    """小红书图片搜索 (需登录Cookie)"""
    from playwright.async_api import async_playwright

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 小红书需要可见浏览器
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},  # 手机比例
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) ...",
        )
        page = await context.new_page()
        await page.goto(f"https://www.xiaohongshu.com/search_result?keyword={query}&type=51", timeout=20000)
        await asyncio.sleep(3)  # 等页面加载
        # 点击笔记卡片
        cards = await page.query_selector_all("section.note-item")
        for card in cards[:count]:
            try:
                await card.click()
                await asyncio.sleep(1.5)
                imgs = await page.query_selector_all(".swiper-slide img")
                for img in imgs[:2]:
                    src = await img.get_attribute("src")
                    if src:
                        results.append(src)
                await page.go_back()
                await asyncio.sleep(1)
            except Exception:
                continue
        await browser.close()
    return results


async def download_images(urls: list[str], city: str, prefix: str = "") -> list[str]:
    """下载图片到 static/photos/{city}/"""
    import httpx

    city_dir = PHOTO_DIR / city
    city_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    async with httpx.AsyncClient(timeout=30) as client:
        for i, url in enumerate(urls):
            try:
                resp = await client.get(url)
                ext = url.split("?")[0].split(".")[-1][:4] or "jpg"
                name = f"{prefix}_{i+1}.{ext}" if prefix else f"{i+1}.{ext}"
                path = city_dir / name
                path.write_bytes(resp.content)
                saved.append(str(path))
            except Exception:
                continue
    return saved


async def scrape_city_images(city: str, spot_names: list[str]):
    """为一个城市的景点抓取图片"""
    print(f"[Scraper] {city}: {len(spot_names)} spots")
    all_saved = []

    for name in spot_names[:5]:  # 每个景点最多5张
        query = f"{city} {name} 风景"
        print(f"  Searching: {query}")
        try:
            urls = await search_baidu_images(query, count=3)
            if urls:
                saved = await download_images(urls, city, name)
                all_saved.extend(saved)
                print(f"    Saved {len(saved)} images")
        except Exception as e:
            print(f"    Failed: {e}")

    return all_saved


# CLI 测试
if __name__ == "__main__":
    async def test():
        print("Testing Baidu image search for 延边...")
        urls = await search_baidu_images("延边 长白山 风景", count=3)
        print(f"Found {len(urls)} URLs")
        if urls:
            saved = await download_images(urls, "延边", "test")
            print(f"Saved to: {saved}")

    asyncio.run(test())
