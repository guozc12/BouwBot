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

# 加载环境变量
load_dotenv()

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
        
        # 只查找发件人为 z.guo1@tue.nl 且未读的邮件
        _, messages = mail.search(None, '(UNSEEN FROM "z.guo1@tue.nl")')
        
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
        address = re.search(r'\d{4}[A-Z]{2} [A-Za-z ]+', info_text)
        address = address.group(0) if address else ''
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
        details, images, details_sections = self.get_house_details(house_info['url'])
        house_info['details'] = details
        if images:
            house_info['images'] = images
        house_info['details_sections'] = details_sections

        # 获取到最近火车站的距离
        house_info['nearest_station'] = self.get_nearest_station(house_info['address'])

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
        print(f"[调试] ChromeDriver 路径: {chromedriver_path}")
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=chrome_options)
        details = ""
        images = []
        details_sections = {}
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
            print("[调试] 已保存完整HTML到 debug_house_detail.html")
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
            print("[调试] details_sections:", details_sections)
            if not details_sections and details_div:
                print("[调试] details_div HTML:", details_div.prettify()[:2000])
            # 提取所有图片链接
            links_div = soup.find("div", id="links")
            if links_div:
                for a in links_div.find_all("a", href=True):
                    images.append(a["href"])
            main_img = soup.find("img", id="myHeightImage")
            if main_img and main_img.get("src"):
                images.insert(0, main_img["src"])
            images = list(dict.fromkeys(images))
        except Exception as e:
            print(f"Error in get_house_details: {e}")
        finally:
            driver.quit()
        return details, images, details_sections
    
    def get_nearest_station(self, address):
        """获取到最近火车站的距离"""
        # 使用 Google Maps API 获取最近的火车站
        try:
            # 搜索最近的火车站
            stations_result = self.gmaps.places_nearby(
                location=self.gmaps.geocode(address)[0]['geometry']['location'],
                keyword='train station',
                radius=5000
            )
            
            if stations_result['results']:
                nearest_station = stations_result['results'][0]
                # 获取步行路线
                directions_result = self.gmaps.directions(
                    address,
                    nearest_station['vicinity'],
                    mode="walking"
                )
                
                if directions_result:
                    return {
                        'station_name': nearest_station['name'],
                        'walking_time': directions_result[0]['legs'][0]['duration']['text'],
                        'distance': directions_result[0]['legs'][0]['distance']['text']
                    }
        except Exception as e:
            print(f"Error getting station info: {e}")
            return None
    
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

if __name__ == "__main__":
    processor = MakelaarslandProcessor()
    while True:
        processor.check_email()
        print("等待10秒后再次检测...")
        time.sleep(10) 