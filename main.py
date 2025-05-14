from flask import Flask, request, send_from_directory
import time
import subprocess
import os
import asyncio
from pyppeteer import launch

app = Flask(__name__)

# 异步函数：使用pyppeteer截取HTML为PNG和提取SVG
async def capture_svg_and_png(html_path, svg_path, png_path):
    browser = await launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = await browser.newPage()
    
    # 设置视口大小
    await page.setViewport({'width': 1280, 'height': 800})
    
    # 加载HTML文件
    await page.goto(f'file://{os.path.abspath(html_path)}')
    
    # 等待SVG元素加载完成
    await page.waitForSelector('svg', {'timeout': 5000})
    
    # 给JavaScript一些时间来完全渲染思维导图
    await asyncio.sleep(2)
    
    # 提取SVG内容
    svg_content = await page.evaluate('''() => {
        const svg = document.querySelector('svg');
        return svg.outerHTML;
    }''')
    
    # 保存SVG文件
    with open(svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    # 截图保存为PNG
    await page.screenshot({'path': png_path, 'fullPage': True})
    
    await browser.close()


@app.route('/upload', methods=['POST'])
def upload_markdown():
    content = request.get_data(as_text=True)
    time_name = str(int(time.time()))
    file_name = time_name + ".md"
    html_name = time_name + ".html"
    svg_name = time_name + ".svg"
    png_name = time_name + ".png"
    
    # 确保data目录存在
    os.makedirs('data', exist_ok=True)
    
    with open(f"data/{file_name}", 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 转换md为html
    html_result = subprocess.run(
        ['npx', 'markmap-cli', f'data/{file_name}', '--no-open', '-o', f'data/{html_name}'],
        capture_output=True,
        text=True)
    
    # 使用pyppeteer异步生成SVG和PNG
    html_path = os.path.join(os.getcwd(), 'data', html_name)
    svg_path = os.path.join(os.getcwd(), 'data', svg_name)
    png_path = os.path.join(os.getcwd(), 'data', png_name)
    
    # 创建事件循环并运行异步函数
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(capture_svg_and_png(html_path, svg_path, png_path))
    except Exception as e:
        print(f"生成SVG和PNG时出错: {e}")
    finally:
        loop.close()
    
    return f'Markdown 文件已保存\n预览链接: http://192.168.3.11:5113/html/{html_name}\n思维导图(SVG): http://192.168.3.11:5113/html/{svg_name}\n图片(PNG): http://192.168.3.11:5113/html/{png_name}'


@app.route('/html/<filename>', methods=['GET'])
def get_html(filename):
    html_dir = 'data'
    return send_from_directory(html_dir, filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003)
