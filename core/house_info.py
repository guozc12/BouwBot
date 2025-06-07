import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from utils.logging_config import logger
from models.house import HouseInfo

class HouseInfoProcessor:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
    
    def get_house_details(self, url: str) -> tuple:
        """获取房屋详细信息"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chromedriver_path = ChromeDriverManager().install()
        if not chromedriver_path.endswith("chromedriver.exe"):
            chromedriver_path = os.path.join(os.path.dirname(chromedriver_path), "chromedriver.exe")
            
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
            email_input.send_keys(self.username)
            password_input.send_keys(self.password)
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
            logger.error(f"Error in get_house_details: {str(e)}")
        finally:
            driver.quit()
            
        return details, images, details_sections, agent_info
    
    def extract_important_info(self, details_sections: dict) -> dict:
        """从详情部分提取重要信息"""
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
                    
        return important_info 