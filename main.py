import os
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from googlemaps import Client
from twilio.rest import Client as TwilioClient
from flask import Flask, render_template
from dotenv import load_dotenv
import time
import json
from datetime import datetime
import re
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from publish_to_github import add_new_house
from selenium.webdriver.common.keys import Keys
import logging
import sys

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('makelaarsland.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

class MakelaarslandProcessor:
    def __init__(self):
        self.email = os.getenv('EMAIL')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.makelaarsland_username = os.getenv('MAKELAARSLAND_USERNAME')
        self.makelaarsland_password = os.getenv('MAKELAARSLAND_PASSWORD')
        self.google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        # 支持多个收件人
        recipients = os.getenv('WHATSAPP_RECIPIENTS', '')
        self.whatsapp_recipients = [
            r.strip() if r.strip().startswith('whatsapp:') else f'whatsapp:{r.strip()}'
            for r in recipients.split(',') if r.strip()
        ]
        
        # 初始化 Google Maps 客户端
        self.gmaps = Client(key=self.google_maps_api_key)
        
        # 初始化 Twilio 客户端
        self.twilio_client = TwilioClient(self.twilio_account_sid, self.twilio_auth_token)
        
    def check_email(self):
        """检查邮箱中的新邮件（只检测未读邮件）"""
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(self.email, self.email_password)
        mail.select("inbox")
        
        # 只查找发件人为 info@makelaarsland.nl 且未读的邮件
        _, messages = mail.search(None, '(UNSEEN FROM "info@makelaarsland.nl")')
        #_, messages = mail.search(None, '(UNSEEN FROM "z.guo1@tue.nl")')
        
        for num in messages[0].split():
            _, msg = mail.fetch(num, '(RFC822)')
            email_body = msg[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # 处理邮件内容
            self.process_email(email_message)
            # 处理后标记为已读
            mail.store(num, '+FLAGS', '\\Seen')
        
        mail.close()
        mail.logout()
    
    def process_email(self, email_message):
        """处理邮件内容"""
        subject = decode_header(email_message["subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset()
                    if charset:
                        try:
                            html_content = payload.decode(charset)
                        except Exception:
                            html_content = payload.decode('utf-8', errors='replace')
                    else:
                        try:
                            html_content = payload.decode('utf-8')
                        except Exception:
                            html_content = payload.decode('latin1', errors='replace')
                    self.extract_house_info(html_content)
    
    def extract_house_info(self, html_content):
        """从HTML内容中提取房屋信息"""
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. 标题和详情页链接
        title_link = soup.find('a', href=True, string=True)
        title = title_link.text.strip() if title_link else ''
        detail_url = title_link['href'] if title_link else ''

        # 2. 地址、价格、面积、房间数、经纪人
        info_text = soup.get_text()
        # 提取街道、门牌、邮编、城市
        street = ''
        house_number = ''
        postcode = ''
        city = ''
        # 匹配如"H. Diemerstraat 37, 3555GR Utrecht"
        m = re.search(r'([A-Za-z\.\-\'\s]+)\s(\d+[A-Za-z]?),?\s*(\d{4}[A-Z]{2})\s+([A-Za-z ]+)', info_text)
        if m:
            street = m.group(1).strip()
            house_number = m.group(2).strip()
            postcode = m.group(3).strip()
            city = m.group(4).strip()
            full_address = f"{street} {house_number}, {postcode} {city}"
        else:
            # 兜底用原有逻辑
            full_address = ''
        address = full_address or (re.search(r'\d{4}[A-Z]{2} [A-Za-z ]+', info_text).group(0) if re.search(r'\d{4}[A-Z]{2} [A-Za-z ]+', info_text) else '')
        price = re.search(r'€ [\d\.,]+ k\.k\.', info_text)
        price = price.group(0) if price else ''
        size_rooms = re.search(r'\d+ m² • \d+ m² • \d+ kamers', info_text)
        size_rooms = size_rooms.group(0) if size_rooms else ''
        agent = re.search(r'[A-Za-z ]+ Makelaardij', info_text)
        agent = agent.group(0) if agent else ''

        # 3. 图片
        img_url = ''

        # 4. "Bekijk details"按钮
        btn = soup.find('a', string=lambda s: s and 'Bekijk details' in s)
        btn_url = btn['href'] if btn else detail_url

        house_info = {
            'title': title,
            'address': address,
            'price': price,
            'size_rooms': size_rooms,
            'agent': agent,
            'images': [],
            'url': btn_url,
            'details': '',
            'nearest_station': {}
        }

        # 获取房屋详细信息（文本和图片）
        details, images, details_sections, agent_info = self.get_house_details(house_info['url'])
        house_info['details'] = details
        if images:
            house_info['images'] = images
        house_info['details_sections'] = details_sections
        house_info['agent_info'] = agent_info

        # 自动提取重要参数
        def extract_param(sections, keys):
            for section in sections.values():
                for k, v in section.items():
                    if k in keys:
                        return v
            return ''
        param_keys = {
            'Woonoppervlakte': ['Woonoppervlakte', 'Oppervlakte', 'Gebruiksoppervlakte'],
            'Inhoud': ['Inhoud'],
            'Bouwjaar': ['Bouwjaar'],
            'Aantal kamers': ['Aantal kamers', 'Kamers'],
            'Aantal badkamers': ['Aantal badkamers', 'Badkamers'],
            'Aantal slaapkamers': ['Aantal slaapkamers', 'Slaapkamers'],
            'Energielabel': ['Energielabel', 'Energielabel woning', 'Energie label']
        }
        important_info = {}
        for key, aliases in param_keys.items():
            val = extract_param(details_sections, aliases)
            important_info[key] = val
        # 增强：从 'Aantal kamers' 提取 'Aantal slaapkamers'
        if not important_info['Aantal slaapkamers']:
            kamers_val = important_info.get('Aantal kamers', '')
            m = re.search(r'(\d+)\s*slaapkamers', kamers_val)
            if m:
                important_info['Aantal slaapkamers'] = m.group(1)
        # 增强：从 Energieklasse 提取 Energielabel
        if not important_info['Energielabel']:
            energielabel_section = details_sections.get('Energielabel', {})
            if isinstance(energielabel_section, dict):
                energieklasse = energielabel_section.get('Energieklasse')
                if energieklasse:
                    important_info['Energielabel'] = energieklasse
        print("details_sections:", json.dumps(details_sections, indent=2, ensure_ascii=False))
        print("important_info:", important_info)
        house_info['important_info'] = important_info

        # 获取到最近火车站的距离
        house_info['nearest_station'] = self.get_nearest_station(house_info['address'])

        # 获取WOZ估值
        house_info['woz_info'] = self.get_woz_info(full_address)

        # 获取移民指数
        postcode_match = re.search(r'(\d{4})[A-Z]{2}', postcode)
        if postcode_match:
            postcode_prefix = postcode_match.group(1)
            house_info['immigration_info'] = self.get_immigration_index(postcode_prefix)
        else:
            house_info['immigration_info'] = "<p style='margin:0;color:#666;'>Geen immigratie informatie beschikbaar</p>"

        # 获取Huispedia链接
        house_info['huispedia_url'] = self.get_huispedia_url(full_address)

        # 新增：自动发布到GitHub Pages，获取filename
        filename = add_new_house(house_info)
        house_info['filename'] = filename
        # 发送WhatsApp消息（此时filename已就绪）
        self.send_whatsapp(house_info)
    
    def get_house_details(self, url):
        """获取房屋详细信息（自动登录+抓取详情页所有文本和图片+结构化分组，增强兼容性+调试输出）"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chromedriver_path = ChromeDriverManager().install()
        if not chromedriver_path.endswith("chromedriver.exe"):
            chromedriver_path = os.path.join(os.path.dirname(chromedriver_path), "chromedriver.exe")
        # print(f"[调试] ChromeDriver 路径: {chromedriver_path}")
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
        details = ""
        images = []
        details_sections = {}
        agent_info = {}
        try:
            # 登录 Makelaarsland
            driver.get("https://mijn.makelaarsland.nl/inloggen")
            wait = WebDriverWait(driver, 15)
            email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
            password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            email_input.send_keys(self.makelaarsland_username)
            password_input.send_keys(self.makelaarsland_password)
            login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            login_btn.click()
            time.sleep(3)
            # 访问房屋页面
            driver.get(url)
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            # 保存完整HTML到本地文件
            with open("debug_house_detail.html", "w", encoding="utf-8") as f:
                f.write(soup.prettify())
            # print("[调试] 已保存完整HTML到 debug_house_detail.html")
            # Makelaarsland参数区块递归解析
            features_module = soup.find('div', id='featuresModule')
            if features_module:
                current_section = None
                for elem in features_module.descendants:
                    if getattr(elem, 'name', None) == 'h3':
                        current_section = elem.get_text(strip=True)
                        details_sections[current_section] = {}
                    elif getattr(elem, 'name', None) == 'div' and 'row' in elem.get('class', []):
                        key_div = elem.find('div', class_='grey')
                        value_div = elem.find('div', class_='darkgrey')
                        if key_div and value_div and current_section:
                            key = key_div.get_text(strip=True)
                            value = value_div.get_text(strip=True)
                            details_sections[current_section][key] = value
            # 兜底：原有h2/h3/strong+table/dl结构
            if not details_sections:
                for section in soup.find_all(['h2', 'h3', 'strong']):
                    section_name = section.get_text(strip=True)
                    table = section.find_next(['table', 'dl'])
                    if table:
                        group = {}
                        for row in table.find_all('tr'):
                            cols = row.find_all(['td', 'th'])
                            if len(cols) == 2:
                                key = cols[0].get_text(strip=True)
                                value = cols[1].get_text(strip=True)
                                group[key] = value
                        for dt in table.find_all('dt'):
                            dd = dt.find_next('dd')
                            if dd:
                                group[dt.get_text(strip=True)] = dd.get_text(strip=True)
                        if group:
                            details_sections[section_name] = group
            # 兼容无结构时的纯文本
            details_div = soup.find("div", class_="object-details") or soup.find("main")
            details = details_div.get_text(separator="\n", strip=True) if details_div else soup.get_text()
            # 调试输出
            # print("[调试] details_sections:", details_sections)
            if not details_sections and details_div:
                # print("[调试] details_div HTML:", details_div.prettify()[:2000])
                pass
            # 提取所有图片链接
            links_div = soup.find("div", id="links")
            if links_div:
                for a in links_div.find_all("a", href=True):
                    images.append(a["href"])
            main_img = soup.find("img", id="myHeightImage")
            if main_img and main_img.get("src"):
                images.insert(0, main_img["src"])
            images = list(dict.fromkeys(images))
            # 抓取Verkopend makelaar卡片
            agent_card = soup.find('h3', string=lambda s: s and 'Verkopend makelaar' in s)
            if agent_card:
                card_div = agent_card.find_parent('div', class_='card')
                if card_div:
                    # 代理名
                    name_p = card_div.find('p')
                    agent_info['name'] = name_p.get_text(strip=True) if name_p else ''
                    # 电话
                    phone_a = card_div.find('a', href=lambda h: h and h.startswith('tel:'))
                    agent_info['phone'] = phone_a.get_text(strip=True) if phone_a else ''
                    # 邮箱
                    email_a = card_div.find('a', href=lambda h: h and h.startswith('mailto:'))
                    agent_info['email'] = email_a.get_text(strip=True) if email_a else ''
        except Exception as e:
            # print(f"[调试] get_house_details agent_info error: {e}")
            print(f"Error in get_house_details: {e}")
        finally:
            driver.quit()
        return details, images, details_sections, agent_info
    
    def get_commute_time(self, origin, destination, mode='transit', departure_time=None):
        """查询指定出发时间的通勤信息（默认公交，支持驾车/步行）"""
        if departure_time is None:
            # 默认下周二早上9点
            from datetime import datetime, timedelta
            today = datetime.now()
            days_ahead = (1 - today.weekday() + 7) % 7  # 1=Tuesday
            if days_ahead == 0:
                days_ahead = 7
            next_tuesday = today + timedelta(days=days_ahead)
            commute_time = next_tuesday.replace(hour=9, minute=0, second=0, microsecond=0)
            departure_time = int(commute_time.timestamp())
        try:
            directions = self.gmaps.directions(
                origin,
                destination,
                mode=mode,
                departure_time=departure_time,
                region='nl',
                language='nl'
            )
            if directions and len(directions) > 0:
                leg = directions[0]['legs'][0]
                return {
                    'duration': leg['duration']['text'],
                    'distance': leg['distance']['text'],
                    'start_address': leg['start_address'],
                    'end_address': leg['end_address'],
                    'summary': directions[0].get('summary', ''),
                    'mode': mode
                }
        except Exception as e:
            print(f"[调试] get_commute_time error: {e}")
            return {
                'duration': 'Niet beschikbaar',
                'distance': 'Niet beschikbaar',
                'start_address': origin,
                'end_address': destination,
                'summary': '',
                'mode': mode
            }

    def get_nearest_station(self, address):
        """获取到最近火车站的距离，并查两大通勤点"""
        # 1. 最近火车站（步行）
        try:
            stations = self.gmaps.places_nearby(
                location=self.gmaps.geocode(address)[0]['geometry']['location'],
                radius=5000,
                type='train_station',
                language='nl'
            )
            if stations['results']:
                nearest = stations['results'][0]
                station_name = nearest['name']
                station_loc = nearest['geometry']['location']
                station_addr = nearest.get('vicinity', '')
                # 步行时间
                walk = self.get_commute_time(address, station_name, mode='walking')
            else:
                station_name = ''
                station_addr = ''
                walk = None
        except Exception as e:
            print(f"[调试] get_nearest_station error: {e}")
            station_name = ''
            station_addr = ''
            walk = None

        # 2. 到 amsterdam science park station
        try:
            science_park = 'Science Park 904, 1098 XH Amsterdam, Netherlands'
            commute_science = self.get_commute_time(address, science_park, mode='transit')
        except Exception as e:
            print(f"[调试] get_science_park_commute error: {e}")
            commute_science = None

        # 3. 到 Eindhoven Station
        try:
            flux_building = 'De Groene Loper 19, 5612 AP Eindhoven, Netherlands'
            commute_flux = self.get_commute_time(address, flux_building, mode='transit')
        except Exception as e:
            print(f"[调试] get_flux_commute error: {e}")
            commute_flux = None

        return {
            'station_name': station_name,
            'station_addr': station_addr,
            'walking_time': walk['duration'] if walk else '',
            'walking_distance': walk['distance'] if walk else '',
            'to_science_park': commute_science,
            'to_flux': commute_flux
        }
    
    def send_whatsapp(self, house_info):
        print("正在尝试发送 WhatsApp 消息...")
        print("from_参数:", f'whatsapp:{self.twilio_phone_number}')
        print("收件人列表:", self.whatsapp_recipients)
        station_info = house_info.get('nearest_station', {}) or {}
        station_text = ''
        if station_info:
            station_text = f"\nNearest station: {station_info.get('station_name', '')}\nWalking time: {station_info.get('walking_time', '')}\nDistance: {station_info.get('distance', '')}"
        github_base_url = "https://guozc12.github.io/makelaarsland-houses/"
        page_url = github_base_url + house_info.get('filename', '')
        body = f"New house alert!\nTitle: {house_info['title']}\nPrice: {house_info['price']}\nAddress: {house_info['address']}\nPage: {page_url}{station_text}"
        for recipient in self.whatsapp_recipients:
            print("to参数:", recipient)
            message = self.twilio_client.messages.create(
                from_=f'whatsapp:{self.twilio_phone_number}',
                body=body,
                to=recipient
            )
            print("消息已发送，Twilio SID:", message.sid, "to", recipient)

    def get_woz_info(self, address):
        """
        自动从 wozwaardeloket.nl 查询房屋的 WOZ 估值。
        :param address: 完整地址字符串
        :return: 估值表格HTML字符串或空字符串
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        import re

        def format_address(addr):
            m = re.match(r'(.+\d+)\s*,\s*(\d{4}[A-Z]{2})\s+([A-Za-z ]+)', addr)
            if m:
                return f"{m.group(1).strip()}, {m.group(2).strip()} {m.group(3).strip()}"
            print(f"[WOZ] 地址格式不正确，未包含街道和门牌: {addr}")
            return ''
        address = format_address(address)
        if not address:
            print("[WOZ] 未能生成正确的查询地址，跳过 WOZ 查询。")
            return ''
        print(f"[WOZ] 查询地址: {address}")

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chromedriver_path = ChromeDriverManager().install()
        if not chromedriver_path.endswith("chromedriver.exe"):
            chromedriver_path = os.path.join(os.path.dirname(chromedriver_path), "chromedriver.exe")
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
        woz_table_html = ""
        try:
            print("[WOZ] 打开网站...")
            driver.get("https://www.wozwaardeloket.nl/")
            wait = WebDriverWait(driver, 30)
            try:
                print("[WOZ] 检查弹窗...")
                modal = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modal__card")))
                try:
                    print("[WOZ] 尝试点击 Ga verder 按钮...")
                    ga_verder_btn = modal.find_element(By.CSS_SELECTOR, ".btn, button")
                    ga_verder_btn.click()
                    print("[WOZ] 已点击 Ga verder 按钮")
                except Exception:
                    print("[WOZ] 尝试点击右上角关闭按钮...")
                    close_btn = modal.find_element(By.CSS_SELECTOR, "button")
                    close_btn.click()
                    print("[WOZ] 已点击关闭按钮")
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal__card")))
                time.sleep(0.5)
            except Exception as e:
                print(f"[WOZ] 没有弹窗或弹窗处理异常: {e}")
            # 健壮地查找输入框
            try:
                print("[WOZ] 等待输入框可点击...")
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                input_box = wait.until(EC.element_to_be_clickable((By.ID, "ggcSearchInput")))
                input_box.click()
                print("[WOZ] 输入框已点击")
            except Exception as e:
                print(f"[WOZ] 查找输入框失败: {e}")
                with open("woz_inputbox_fail.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                driver.quit()
                return "WOZ页面结构异常，未找到输入框"
            time.sleep(0.5)
            input_box.clear()
            for char in address:
                input_box.send_keys(char)
                time.sleep(0.05)
            print(f"[WOZ] 地址已输入: {input_box.get_attribute('value')}")
            time.sleep(0.5)
            try:
                search_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .search-button")
                search_button.click()
                print("[WOZ] 已点击搜索按钮")
            except:
                input_box.send_keys(Keys.ENTER)
                print("[WOZ] 已按回车键搜索")
            time.sleep(5)
            print("[WOZ] 当前页面URL:", driver.current_url)
            print("[WOZ] 页面标题:", driver.title)
            with open("woz_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("[WOZ] 已保存页面源码到 woz_debug.html")
            # 直接查找 WOZ 行
            print("[WOZ] 直接查找 WOZ 行 tr.waarden-row ...")
            time.sleep(2)
            # 先在主页面查找
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.waarden-row")
            print(f"[WOZ] 主页面找到的行数: {len(rows)}")
            if rows:
                woz_table_html = "<table style='width:100%;border-collapse:collapse;'><thead><tr><th>Peildatum</th><th>WOZ-waarde</th></tr></thead><tbody>"
                for row in rows:
                    date = row.find_element(By.CSS_SELECTOR, ".wozwaarde-datum").text.strip()
                    value = row.find_element(By.CSS_SELECTOR, ".wozwaarde-waarde").text.strip()
                    woz_table_html += f"<tr><td>{date}</td><td>{value}</td></tr>"
                woz_table_html += "</tbody></table>"
            else:
                print("[WOZ] 未找到 WOZ 数据")
                woz_table_html = "<p style='margin:0;color:#666;'>Geen WOZ informatie beschikbaar</p>"
        except Exception as e:
            print(f"[WOZ] 发生错误: {e}")
            woz_table_html = "<p style='margin:0;color:#666;'>Geen WOZ informatie beschikbaar</p>"
        finally:
            driver.quit()
        return woz_table_html

    def get_immigration_index(self, postcode):
        """
        从 allochtonenmeter.nl 获取移民指数数据
        :param postcode: 邮编前4位数字
        :return: 移民指数数据HTML字符串或空字符串
        """
        import requests
        from bs4 import BeautifulSoup
        import time

        try:
            print(f"[Immigration] 获取邮编 {postcode} 的移民数据...")
            url = f"http://www.allochtonenmeter.nl/?postcode={postcode}"
            response = requests.get(url)
            response.raise_for_status()  # 检查请求是否成功
            
            print("[Immigration] 解析页面内容...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找结果表格
            table = soup.find('table')
            if table:
                print("[Immigration] 找到数据表格，开始提取...")
                # 提取表格数据并重新格式化
                rows = table.find_all('tr')
                print(f"[Immigration] 找到 {len(rows)} 行数据")
                
                immigration_html = "<table style='width:100%;border-collapse:collapse;'>"
                for i, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        print(f"[Immigration] 处理第 {i+1} 行，包含 {len(cells)} 个单元格")
                        immigration_html += "<tr>"
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            print(f"[Immigration] 单元格内容: {cell_text}")
                            immigration_html += f"<td>{cell_text}</td>"
                        immigration_html += "</tr>"
                immigration_html += "</table>"
                print("[Immigration] 表格数据提取完成")
            else:
                print("[Immigration] 未找到数据表格")
                immigration_html = "<p style='margin:0;color:#666;'>Geen immigratie informatie beschikbaar</p>"
                
        except Exception as e:
            print(f"[Immigration] 发生错误: {str(e)}")
            print(f"[Immigration] 错误类型: {type(e).__name__}")
            import traceback
            print(f"[Immigration] 错误堆栈: {traceback.format_exc()}")
            immigration_html = "<p style='margin:0;color:#666;'>Geen immigratie informatie beschikbaar</p>"
            
        return immigration_html

    def get_huispedia_url(self, address):
        """
        根据地址生成Huispedia的URL
        :param address: 完整地址字符串，格式如 "Belter Wijdestraat 17, 1316JR Almere"
        :return: Huispedia URL或空字符串
        """
        try:
            # 匹配地址格式：街道名 门牌号, 邮编 城市
            m = re.match(r'([A-Za-z\.\-\'\s]+)\s(\d+[A-Za-z]?),?\s*(\d{4}[A-Z]{2})\s+([A-Za-z ]+)', address)
            if m:
                street = m.group(1).strip().lower().replace(' ', '-')
                house_number = m.group(2).strip().lower()
                postcode = m.group(3).strip().lower()
                city = m.group(4).strip().lower()
                
                # 构建URL
                url = f"https://huispedia.nl/{city}/{postcode}/{street}/{house_number}"
                print(f"[Huispedia] 生成URL: {url}")
                return url
            else:
                print(f"[Huispedia] 地址格式不正确: {address}")
                return ""
        except Exception as e:
            print(f"[Huispedia] 生成URL时发生错误: {str(e)}")
            return ""

def main():
    processor = MakelaarslandProcessor()
    while True:
        try:
            logging.info("Starting new check cycle...")
            processor.check_email()
            logging.info("Check cycle completed successfully")
            # 每10秒检查一次
            time.sleep(10)
        except Exception as e:
            logging.error(f"Error occurred: {str(e)}", exc_info=True)
            # 发生错误时等待1分钟后重试
            time.sleep(10)

if __name__ == "__main__":
    main() 