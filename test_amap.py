"""
高德地图 API 2.0 安全密钥测试

使用方法:
1. 编辑 config.py → amap.route_key 填你的 Key
2. 编辑 config.py → amap.secret 填你的安全密钥
3. 运行: python test_amap.py
4. 浏览器打开 test_amap.html
"""

import webbrowser
import os

from config import default_config

# 从 config.py 读取，避免硬编码真实密钥
key = default_config.amap.route_key
secret = default_config.amap.secret

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>高德地图测试</title>
<style>
  body{{margin:0;padding:20px;font-family:sans-serif}}
  #container{{width:100%;height:500px;border-radius:12px}}
  .info{{background:#e8f5e9;padding:12px;border-radius:8px;margin-bottom:16px;font-family:monospace}}
  .err{{background:#fce4ec}}
</style>
</head>
<body>
<h2>🗺️ 高德地图 2.0 安全密钥测试</h2>
<div class="info">
  Key: {key}<br>
  Secret: {'***'+secret[-4:] if len(secret)>4 else '(未配置)'}
</div>
<div id="container"></div>

<script>
window._AMapSecurityConfig = {{
    securityJsCode: "{secret}"
}};
</script>
<script src="https://webapi.amap.com/maps?v=2.0&key={key}&plugin=AMap.Polyline,AMap.Marker"></script>
<script>
try {{
    var m = new AMap.Map('container', {{
        zoom: 7,
        center: [114.39, 36.10],
        mapStyle: 'amap://styles/light'
    }});
    var mk = new AMap.Marker({{
        position: [114.39, 36.10],
        title: '安阳测试点'
    }});
    m.add(mk);
    document.querySelector('.info').innerHTML += '<br>✅ 地图加载成功！';
}} catch(e) {{
    document.querySelector('.info').innerHTML += '<br>❌ 错误: ' + e.message;
    document.querySelector('.info').classList.add('err');
}}
</script>
</body>
</html>"""

filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_amap.html")
with open(filepath, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ 测试文件已生成: {filepath}")
print(f"   Key: {key}")
print(f"   Secret: {'已配置' if len(secret) > 4 else '未配置！请在 config.py 填写 amap.secret'}")
print()
webbrowser.open(f"file:///{filepath.replace(chr(92), '/')}")
