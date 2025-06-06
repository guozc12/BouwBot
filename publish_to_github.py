import os
import json
import datetime
from jinja2 import Template
import subprocess

# 配置
REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'makelaarsland-houses'))  # 指向子仓库目录
HOUSE_TEMPLATE = os.path.join(REPO_PATH, 'house_template.html')
INDEX_TEMPLATE = os.path.join(REPO_PATH, 'index_template.html')
HOUSES_JSON = os.path.join(REPO_PATH, 'houses.json')  # 存储所有房源信息

# 1. 渲染房源详情页

def render_house_page(house, filename):
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