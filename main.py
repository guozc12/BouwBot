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
from utils.config import Config
from utils.logging_config import logger
from core.email_handler import EmailHandler
from core.house_info import HouseInfoProcessor
from services.maps_service import MapsService
from services.whatsapp_service import WhatsAppService
from services.email_service import EmailService
from services.woz_service import WOZService
from services.immigration_service import ImmigrationService
from services.huispedia_service import HuispediaService
from models.house import HouseInfo

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
        # 初始化配置
        self.config = Config()
        
        # 初始化各个服务
        self.email_handler = EmailHandler(self.config.EMAIL, self.config.EMAIL_PASSWORD)
        self.house_processor = HouseInfoProcessor(self.config.MAKELAARSLAND_USERNAME, self.config.MAKELAARSLAND_PASSWORD)
        self.maps_service = MapsService(self.config.GOOGLE_MAPS_API_KEY)
        self.whatsapp_service = WhatsAppService(
            self.config.TWILIO_ACCOUNT_SID,
            self.config.TWILIO_AUTH_TOKEN,
            self.config.TWILIO_PHONE_NUMBER,
            self.config.get_whatsapp_recipients()
        )
        self.email_service = EmailService(
            self.config.EMAIL,
            self.config.EMAIL_PASSWORD,
            self.config.get_email_recipients()
        )
        self.woz_service = WOZService()
        self.immigration_service = ImmigrationService()
        self.huispedia_service = HuispediaService()
    
    def process_house(self, house_data: dict) -> HouseInfo:
        """处理单个房屋信息"""
        # 获取详细信息
        details, images, details_sections, agent_info = self.house_processor.get_house_details(house_data['url'])
        house_data['details'] = details
        house_data['images'] = images
        house_data['details_sections'] = details_sections
        house_data['agent_info'] = agent_info
        
        # 提取重要信息
        house_data['important_info'] = self.house_processor.extract_important_info(details_sections)
        
        # 获取到最近火车站的距离
        house_data['nearest_station'] = self.maps_service.get_nearest_station(house_data['address'])
        
        # 获取WOZ估值
        house_data['woz_info'] = self.woz_service.get_woz_info(house_data['address'])
        
        # 获取移民指数
        postcode_match = re.search(r'(\d{4})[A-Z]{2}', house_data['address'])
        if postcode_match:
            postcode_prefix = postcode_match.group(1)
            house_data['immigration_info'] = self.immigration_service.get_immigration_index(postcode_prefix)
        else:
            house_data['immigration_info'] = "<p style='margin:0;color:#666;'>Geen immigratie informatie beschikbaar</p>"
        
        # 获取Huispedia链接
        house_data['huispedia_url'] = self.huispedia_service.get_huispedia_url(house_data['address'])
        
        # 发布到GitHub Pages
        filename = add_new_house(house_data)
        house_data['filename'] = filename
        
        # 转换为HouseInfo对象
        return HouseInfo.from_dict(house_data)
    
    def run(self):
        """主循环"""
        while True:
            try:
                logger.info("Starting new check cycle...")
                
                # 检查新邮件
                for house_data in self.email_handler.check_email():
                    if house_data:
                        # 处理房屋信息
                        house_info = self.process_house(house_data)
                        
                        # 发送WhatsApp消息
                        self.whatsapp_service.send_house_info(house_info)
                        
                        # 发送邮件
                        self.email_service.send_house_info(house_info)
                
                logger.info("Check cycle completed successfully")
                # 每10秒检查一次
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error occurred: {str(e)}", exc_info=True)
                # 发生错误时等待10秒后重试
                time.sleep(10)

def main():
    processor = MakelaarslandProcessor()
    processor.run()

if __name__ == "__main__":
    main() 