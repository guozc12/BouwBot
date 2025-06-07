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
        logging.FileHandler('makelaarsland.log', encoding='utf-8'),
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
        """Check for new emails (unread only)"""
        logging.info("Starting email check...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(self.email, self.email_password)
        mail.select("inbox")
        
        # Search for unread emails from info@makelaarsland.nl
        _, messages = mail.search(None, '(UNSEEN FROM "info@makelaarsland.nl")')
        logging.info(f"Found {len(messages[0].split())} unread emails")
        
        for num in messages[0].split():
            logging.info(f"Processing email #{num.decode()}")
            _, msg = mail.fetch(num, '(RFC822)')
            email_body = msg[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # Print email basic info
            subject = decode_header(email_message["subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            logging.info(f"Email subject: {subject}")
            logging.info(f"From: {email_message['from']}")
            logging.info(f"Date: {email_message['date']}")
            
            # Process email content
            self.process_email(email_message)
            # Mark as read after processing
            mail.store(num, '+FLAGS', '\\Seen')
            logging.info(f"Email #{num.decode()} processed and marked as read")
        
        mail.close()
        mail.logout()
        logging.info("Email check completed")
    
    def process_email(self, email_message):
        """Process email content"""
        subject = decode_header(email_message["subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        logging.info(f"Starting to process email content: {subject}")
            
        if email_message.is_multipart():
            logging.info("Detected multipart email")
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_transfer_encoding = part.get('Content-Transfer-Encoding', '').lower()
                logging.info(f"Processing email part - Type: {content_type}, Encoding: {content_transfer_encoding}")
                
                # Handle text/html content
                if content_type == "text/html":
                    try:
                        # Get the payload
                        payload = part.get_payload(decode=True)
                        
                        # Try to determine the charset
                        charset = part.get_content_charset()
                        logging.info(f"Detected charset: {charset}")
                        
                        # Decode the content based on the encoding
                        if content_transfer_encoding == 'base64':
                            logging.info("Detected Base64 encoded content")
                            try:
                                html_content = payload.decode(charset if charset else 'utf-8')
                                logging.info("Base64 content decoded successfully")
                            except UnicodeDecodeError:
                                logging.warning(f"Failed to decode with charset {charset}, trying latin1")
                                html_content = payload.decode('latin1', errors='replace')
                        else:
                            # For non-base64 content, try to decode with the specified charset
                            try:
                                html_content = payload.decode(charset if charset else 'utf-8')
                                logging.info("Content decoded successfully")
                            except UnicodeDecodeError:
                                logging.warning(f"Failed to decode with charset {charset}, trying latin1")
                                html_content = payload.decode('latin1', errors='replace')
                        
                        # Process the decoded HTML content
                        logging.info("Starting to extract house information...")
                        self.extract_house_info(html_content)
                        logging.info("House information extraction completed")
                        
                    except Exception as e:
                        logging.error(f"Error processing email part: {str(e)}")
                        continue
        else:
            logging.info("Detected single part email")
            try:
                payload = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset()
                logging.info(f"Single part email charset: {charset}")
                html_content = payload.decode(charset if charset else 'utf-8')
                self.extract_house_info(html_content)
            except Exception as e:
                logging.error(f"Error processing single part email: {str(e)}")
    
    def extract_house_info(self, html_content):
        """Extract house information from HTML content"""
        logging.info("Starting HTML content parsing...")
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Title and detail page link
        title_link = soup.find('a', href=True, string=True)
        title = title_link.text.strip() if title_link else ''
        detail_url = title_link['href'] if title_link else ''
        logging.info(f"Extracted title: {title}")
        logging.info(f"Detail page URL: {detail_url}")

        # 2. Address, price, size, rooms, agent
        info_text = soup.get_text()
        logging.info("Starting address extraction...")
        # Extract street, house number, postcode, city
        street = ''
        house_number = ''
        postcode = ''
        city = ''
        # Match pattern like "H. Diemerstraat 37, 3555GR Utrecht"
        m = re.search(r'([A-Za-z\.\-\'\s]+)\s(\d+[A-Za-z]?),?\s*(\d{4}[A-Z]{2})\s+([A-Za-z ]+)', info_text)
        if m:
            street = m.group(1).strip()
            house_number = m.group(2).strip()
            postcode = m.group(3).strip()
            city = m.group(4).strip()
            full_address = f"{street} {house_number}, {postcode} {city}"
            logging.info(f"Successfully matched address: {full_address}")
        else:
            logging.warning("Failed to match complete address format")
            full_address = ''
        address = full_address or (re.search(r'\d{4}[A-Z]{2} [A-Za-z ]+', info_text).group(0) if re.search(r'\d{4}[A-Z]{2} [A-Za-z ]+', info_text) else '')
        logging.info(f"Final address: {address}")
        
        price = re.search(r'€ [\d\.,]+ k\.k\.', info_text)
        price = price.group(0) if price else ''
        logging.info(f"Price: {price}")
        
        size_rooms = re.search(r'\d+ m² • \d+ m² • \d+ kamers', info_text)
        size_rooms = size_rooms.group(0) if size_rooms else ''
        logging.info(f"Size and rooms: {size_rooms}")
        
        agent = re.search(r'[A-Za-z ]+ Makelaardij', info_text)
        agent = agent.group(0) if agent else ''
        logging.info(f"Agent: {agent}")

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
        """Send house information via WhatsApp"""
        logging.info("Starting WhatsApp message preparation...")
        try:
            # Prepare simplified message content
            message = f"🏠 New House Alert!\n\n"
            message += f"Title: {house_info['title']}\n"
            message += f"Address: {house_info['address']}\n"
            message += f"Price: {house_info['price']}\n"
            message += f"Details: {house_info['size_rooms']}\n"
            message += f"Agent: {house_info['agent']}\n"
            
            if house_info.get('nearest_station'):
                station_info = house_info['nearest_station']
                message += f"\n🚉 Nearest Station: {station_info.get('name', 'N/A')}\n"
                message += f"Distance: {station_info.get('distance', 'N/A')}\n"
                message += f"Walking Time: {station_info.get('walking_time', 'N/A')}\n"
            
            message += f"\n🔗 View Details: {house_info['url']}"
            
            logging.info(f"Message length: {len(message)} characters")
            
            # Send message to each recipient
            for recipient in self.whatsapp_recipients:
                try:
                    logging.info(f"Sending message to: {recipient}")
                    logging.info(f"From: whatsapp:{self.twilio_phone_number}")
                    message = self.twilio_client.messages.create(
                        body=message,
                        from_=f'whatsapp:{self.twilio_phone_number}',
                        to=recipient
                    )
                    logging.info(f"Message sent successfully")
                    logging.info(f"Message SID: {message.sid}")
                    logging.info(f"Message status: {message.status}")
                except Exception as e:
                    logging.error(f"Failed to send message to {recipient}: {str(e)}")
                    continue
                
        except Exception as e:
            logging.error(f"Error in WhatsApp message preparation: {str(e)}")
            raise

    def get_woz_info(self, address):
        """Get WOZ information from walterliving.com"""
        logging.info(f"[WOZ] Querying address: {address}")
        try:
            m = re.match(r'([A-Za-z\.\-\'\s]+)\s(\d+[A-Za-z]?),?\s*(\d{4}[A-Z]{2})\s+([A-Za-z ]+)', address)
            if not m:
                logging.error("[WOZ] Invalid address format")
                return None
            street = m.group(1).strip().lower().replace(' ', '-')
            house_number = m.group(2).strip().lower()
            city = m.group(4).strip().lower()
            url = f"https://walterliving.com/report/{street}-{house_number}-{city}"
            logging.info(f"[WOZ] Generated URL: {url}")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            woz_list = soup.find('ul', class_='group')
            if not woz_list:
                logging.error("[WOZ] No WOZ data found")
                return None
            woz_data = []
            for item in woz_list.find_all('li', class_='timeline-events__item'):
                try:
                    woz_type = item.find('span', class_='timeline-events__item__type')
                    if not woz_type or 'WOZ' not in woz_type.text:
                        continue
                    # 提取年份
                    year_match = re.search(r'WOZ\s*(\d{4})', woz_type.text)
                    year = year_match.group(1) if year_match else ''
                    # 提取金额
                    value_div = item.find('div', class_='timeline-events__item__content')
                    amount_match = re.search(r'€\s*[\d\.]+', value_div.text) if value_div else None
                    amount = amount_match.group(0) if amount_match else ''
                    # 提取百分比
                    percent_match = re.search(r'(\d{1,2},\d)%', value_div.text) if value_div else None
                    percent = percent_match.group(1) + '%' if percent_match else ''
                    if year and amount:
                        woz_data.append(f"WOZ {year}: {amount} {f'({percent})' if percent else ''}")
                except Exception as e:
                    logging.error(f"[WOZ] Error parsing WOZ item: {str(e)}")
                    continue
            if not woz_data:
                logging.error("[WOZ] No valid WOZ data found")
                return None
            woz_html = "<ul class='woz-data'>" + ''.join(f"<li>{row}</li>" for row in woz_data) + "</ul>"
            return woz_html
        except Exception as e:
            logging.error(f"[WOZ] Error in WOZ info retrieval: {str(e)}")
            return None

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