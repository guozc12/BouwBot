import os
import json
import datetime
from jinja2 import Template
import subprocess
import re

# 配置
REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'makelaarsland-houses'))  # 指向子仓库目录
HOUSE_TEMPLATE = os.path.join(REPO_PATH, 'house_template.html')
INDEX_TEMPLATE = os.path.join(REPO_PATH, 'index_template.html')
HOUSES_JSON = os.path.join(REPO_PATH, 'houses.json')  # 存储所有房源信息

# 1. 渲染房源详情页

def render_house_page(house, filename):
    # 解析详情文本，提取重要信息和其他信息
    details = house.get('details', '')
    important_info = {}
    other_info = {}
    
    # 定义重要信息的键值对模式
    important_patterns = {
        'Woonoppervlakte': r'Woonoppervlakte:\s*([^\n]+)',
        'Perceeloppervlakte': r'Perceeloppervlakte:\s*([^\n]+)',
        'Aantal kamers': r'Aantal kamers:\s*([^\n]+)',
        'Aantal slaapkamers': r'Aantal slaapkamers:\s*([^\n]+)',
        'Bouwjaar': r'Bouwjaar:\s*([^\n]+)',
        'Energielabel': r'Energielabel:\s*([^\n]+)',
        'Type woning': r'Type woning:\s*([^\n]+)',
        'Type bouw': r'Type bouw:\s*([^\n]+)',
        'Ligging': r'Ligging:\s*([^\n]+)',
        'Tuin': r'Tuin:\s*([^\n]+)',
        'Garage': r'Garage:\s*([^\n]+)',
        'Parkeren': r'Parkeren:\s*([^\n]+)',
    }
    
    # 提取重要信息
    for key, pattern in important_patterns.items():
        match = re.search(pattern, details, re.IGNORECASE)
        if match:
            important_info[key] = match.group(1).strip()
    
    # 将剩余信息按段落分类
    paragraphs = [p.strip() for p in details.split('\n') if p.strip()]
    current_section = None
    
    for para in paragraphs:
        # 检查是否是新的段落标题
        if ':' in para and len(para.split(':')) == 2:
            current_section = para
            other_info[current_section] = []
        elif current_section:
            other_info[current_section].append(para)
    
    # 更新 house 字典，添加解析后的信息
    house['important_info'] = important_info
    house['other_info'] = other_info
    
    # 读取并渲染模板
    with open(HOUSE_TEMPLATE, encoding='utf-8') as f:
        template = Template(f.read())
    html = template.render(**house)
    with open(os.path.join(REPO_PATH, filename), 'w', encoding='utf-8') as f:
        f.write(html)

# 2. 渲染主页面

def render_index_page(houses):
    with open(INDEX_TEMPLATE, encoding='utf-8') as f:
        template = Template(f.read())
    html = template.render(houses=houses)
    with open(os.path.join(REPO_PATH, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)

# 3. 自动git add/commit/push

def git_push(commit_msg):
    subprocess.run(['git', 'add', '.'], cwd=REPO_PATH)
    subprocess.run(['git', 'commit', '-m', commit_msg], cwd=REPO_PATH)
    subprocess.run(['git', 'push'], cwd=REPO_PATH)

# 4. 新增房源并发布

def add_new_house(house_info):
    # 生成唯一文件名
    now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"house_{now}.html"
    house_info['filename'] = filename

    # 读取/更新houses.json
    if os.path.exists(HOUSES_JSON):
        with open(HOUSES_JSON, encoding='utf-8') as f:
            houses = json.load(f)
    else:
        houses = []
    houses.insert(0, house_info)  # 新房源放最前
    with open(HOUSES_JSON, 'w', encoding='utf-8') as f:
        json.dump(houses, f, ensure_ascii=False, indent=2)

    # 渲染详情页和主页面
    render_house_page(house_info, filename)
    render_index_page(houses)
    # 推送到GitHub
    git_push(f"add house: {house_info.get('title', '')}")
    return filename

# 示例用法（你可以在主流程里调用这个函数）
if __name__ == '__main__':
    # 示例房源数据
    house_info = {
        'title': 'Alfred Nobellaan 42',
        'price': '€ 565.000 k.k.',
        'address': '3731DW De Bilt',
        'size_rooms': '135 m² • 154 m² • 6 kamers',
        'agent': 'Thea Geerts Makelaardij',
        'images': ['https://media.nvm.nl/256x/9248bc17-5450-458e-b4cf-12043b532dda'],
        'details': 'Some details about the house...\nMore info here.',
        'nearest_station': {
            'station_name': 'Utrecht Centraal',
            'walking_time': '15 min',
            'distance': '1.2 km'
        }
    }
    add_new_house(house_info) 