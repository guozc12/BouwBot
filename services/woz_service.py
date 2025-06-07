import re
import requests
from bs4 import BeautifulSoup
from utils.logging_config import logger

class WOZService:
    def get_woz_info(self, address: str) -> str:
        """从walterliving.com获取WOZ信息"""
        logger.info(f"[WOZ] Querying address: {address}")
        try:
            m = re.match(r'([A-Za-z\.\-\'\s]+)\s(\d+[A-Za-z]?),?\s*(\d{4}[A-Z]{2})\s+([A-Za-z ]+)', address)
            if not m:
                logger.error("[WOZ] Invalid address format")
                return None
                
            street = m.group(1).strip().lower().replace(' ', '-')
            house_number = m.group(2).strip().lower()
            city = m.group(4).strip().lower()
            url = f"https://walterliving.com/report/{street}-{house_number}-{city}"
            logger.info(f"[WOZ] Generated URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            woz_list = soup.find('ul', class_='group')
            if not woz_list:
                logger.error("[WOZ] No WOZ data found")
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
                    logger.error(f"[WOZ] Error parsing WOZ item: {str(e)}")
                    continue
                    
            if not woz_data:
                logger.error("[WOZ] No valid WOZ data found")
                return None
                
            woz_html = "<ul class='woz-data'>" + ''.join(f"<li>{row}</li>" for row in woz_data) + "</ul>"
            return woz_html
            
        except Exception as e:
            logger.error(f"[WOZ] Error in WOZ info retrieval: {str(e)}")
            return None 