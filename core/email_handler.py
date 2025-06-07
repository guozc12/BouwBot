import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from utils.logging_config import logger
import re

class EmailHandler:
    def __init__(self, email_address: str, email_password: str):
        self.email = email_address
        self.password = email_password
    
    def check_email(self):
        """检查新邮件（仅未读）"""
        logger.info("Starting email check...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(self.email, self.password)
        mail.select("inbox")
        
        # 搜索来自 info@makelaarsland.nl 的未读邮件
        _, messages = mail.search(None, '(UNSEEN FROM "info@makelaarsland.nl")')
        logger.info(f"Found {len(messages[0].split())} unread emails")
        
        for num in messages[0].split():
            logger.info(f"Processing email #{num.decode()}")
            _, msg = mail.fetch(num, '(RFC822)')
            email_body = msg[0][1]
            email_message = email.message_from_bytes(email_body)
            
            # 打印邮件基本信息
            subject = decode_header(email_message["subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            logger.info(f"Email subject: {subject}")
            logger.info(f"From: {email_message['from']}")
            logger.info(f"Date: {email_message['date']}")
            
            # 处理邮件内容
            yield self.process_email(email_message)
            
            # 标记为已读
            mail.store(num, '+FLAGS', '\\Seen')
            logger.info(f"Email #{num.decode()} processed and marked as read")
        
        mail.close()
        mail.logout()
        logger.info("Email check completed")
    
    def process_email(self, email_message):
        """处理邮件内容"""
        subject = decode_header(email_message["subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        logger.info(f"Starting to process email content: {subject}")
            
        if email_message.is_multipart():
            logger.info("Detected multipart email")
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_transfer_encoding = part.get('Content-Transfer-Encoding', '').lower()
                logger.info(f"Processing email part - Type: {content_type}, Encoding: {content_transfer_encoding}")
                
                # 处理 text/html 内容
                if content_type == "text/html":
                    try:
                        # 获取内容
                        payload = part.get_payload(decode=True)
                        
                        # 尝试确定字符集
                        charset = part.get_content_charset()
                        logger.info(f"Detected charset: {charset}")
                        
                        # 根据编码解码内容
                        if content_transfer_encoding == 'base64':
                            logger.info("Detected Base64 encoded content")
                            try:
                                html_content = payload.decode(charset if charset else 'utf-8')
                                logger.info("Base64 content decoded successfully")
                            except UnicodeDecodeError:
                                logger.warning(f"Failed to decode with charset {charset}, trying latin1")
                                html_content = payload.decode('latin1', errors='replace')
                        else:
                            # 对于非base64内容，尝试使用指定的字符集解码
                            try:
                                html_content = payload.decode(charset if charset else 'utf-8')
                                logger.info("Content decoded successfully")
                            except UnicodeDecodeError:
                                logger.warning(f"Failed to decode with charset {charset}, trying latin1")
                                html_content = payload.decode('latin1', errors='replace')
                        
                        # 处理解码后的HTML内容
                        logger.info("Starting to extract house information...")
                        return self.extract_house_info(html_content)
                        
                    except Exception as e:
                        logger.error(f"Error processing email part: {str(e)}")
                        continue
        else:
            logger.info("Detected single part email")
            try:
                payload = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset()
                logger.info(f"Single part email charset: {charset}")
                html_content = payload.decode(charset if charset else 'utf-8')
                return self.extract_house_info(html_content)
            except Exception as e:
                logger.error(f"Error processing single part email: {str(e)}")
                return None
    
    def extract_house_info(self, html_content):
        """从HTML内容中提取房屋信息"""
        logger.info("Starting HTML content parsing...")
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. 标题和详情页链接
        title_link = soup.find('a', href=True, string=True)
        title = title_link.text.strip() if title_link else ''
        detail_url = title_link['href'] if title_link else ''
        logger.info(f"Extracted title: {title}")
        logger.info(f"Detail page URL: {detail_url}")

        # 2. 地址、价格、面积、房间数、中介
        info_text = soup.get_text()
        logger.info("Starting address extraction...")
        
        # 提取街道、门牌号、邮编、城市
        street = ''
        house_number = ''
        postcode = ''
        city = ''
        # 匹配模式如 "H. Diemerstraat 37, 3555GR Utrecht"
        m = re.search(r'([A-Za-z\.\-\'\s]+)\s(\d+[A-Za-z]?),?\s*(\d{4}[A-Z]{2})\s+([A-Za-z ]+)', info_text)
        if m:
            street = m.group(1).strip()
            house_number = m.group(2).strip()
            postcode = m.group(3).strip()
            city = m.group(4).strip()
            full_address = f"{street} {house_number}, {postcode} {city}"
            logger.info(f"Successfully matched address: {full_address}")
        else:
            logger.warning("Failed to match complete address format")
            full_address = ''
            
        address = full_address or (re.search(r'\d{4}[A-Z]{2} [A-Za-z ]+', info_text).group(0) if re.search(r'\d{4}[A-Z]{2} [A-Za-z ]+', info_text) else '')
        logger.info(f"Final address: {address}")
        
        price = re.search(r'€ [\d\.,]+ k\.k\.', info_text)
        price = price.group(0) if price else ''
        logger.info(f"Price: {price}")
        
        size_rooms = re.search(r'\d+ m² • \d+ m² • \d+ kamers', info_text)
        size_rooms = size_rooms.group(0) if size_rooms else ''
        logger.info(f"Size and rooms: {size_rooms}")
        
        agent = re.search(r'[A-Za-z ]+ Makelaardij', info_text)
        agent = agent.group(0) if agent else ''
        logger.info(f"Agent: {agent}")

        # 3. 图片
        img_url = ''

        # 4. "Bekijk details"按钮
        btn = soup.find('a', string=lambda s: s and 'Bekijk details' in s)
        btn_url = btn['href'] if btn else detail_url

        return {
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