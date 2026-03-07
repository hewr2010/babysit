#!/usr/bin/env python3
"""测试照片EXIF时间读取"""
import time
import requests
from playwright.sync_api import sync_playwright

def test_photo_exif():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("📱 访问应用...")
        page.goto('http://localhost:8080', wait_until='networkidle', timeout=15000)
        time.sleep(3)
        
        print("\n📸 测试照片EXIF时间...")
        
        # 找到照片
        photos = page.locator('img[src*="/thumb/"]').all()
        print(f"找到 {len(photos)} 张照片")
        
        if photos:
            # 触发第一张照片的缩略图加载（会读取EXIF）
            first_photo = photos[0]
            src = first_photo.get_attribute('src')
            print(f"\n加载缩略图: {src}")
            
            # 等待缩略图加载完成
            time.sleep(5)
            
            # 刷新页面，重新获取文件列表（应该已经有EXIF缓存了）
            print("\n刷新相册数据...")
            page.goto('http://localhost:8080/api/album/refresh', wait_until='networkidle')
            time.sleep(2)
            
            # 检查EXIF缓存
            print("\n检查EXIF缓存...")
            try:
                import json
                from pathlib import Path
                cache_file = Path('/Users/hwr/storage/babysit/babysit/data/cache/exif_times.json')
                if cache_file.exists():
                    with open(cache_file) as f:
                        exif_cache = json.load(f)
                    print(f"EXIF缓存条目数: {len(exif_cache)}")
                    for filename, data in list(exif_cache.items())[:5]:
                        print(f"  {filename}: {data['date']} {data['time']}")
                else:
                    print("  ⚠️ EXIF缓存文件不存在")
            except Exception as e:
                print(f"  ❌ 读取缓存失败: {e}")
            
            # 重新访问应用
            print("\n重新访问应用查看效果...")
            page.goto('http://localhost:8080', wait_until='networkidle')
            time.sleep(3)
            
            # 点击照片查看时间
            photos = page.locator('img[src*="/thumb/"]').all()
            if photos:
                photos[0].click()
                time.sleep(2)
                
                viewer = page.locator('.viewer-overlay')
                if viewer.is_visible():
                    photo_info = page.locator('.photo-info').first
                    info_text = photo_info.text_content()
                    print(f"\n照片时间信息: {info_text}")
                    
                    if '2026-03-02' in info_text:
                        print("⚠️ 仍然显示3月2日（网盘上传日期）")
                    else:
                        print("✅ 显示了不同的日期（EXIF拍摄日期）")
        
        browser.close()
        print("\n✅ 测试完成")

if __name__ == '__main__':
    test_photo_exif()
