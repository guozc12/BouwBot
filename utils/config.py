import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # Email配置
    EMAIL = os.getenv('EMAIL')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    
    # Makelaarsland配置
    MAKELAARSLAND_USERNAME = os.getenv('MAKELAARSLAND_USERNAME')
    MAKELAARSLAND_PASSWORD = os.getenv('MAKELAARSLAND_PASSWORD')
    
    # Google Maps配置
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    
    # Twilio配置
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    
    # WhatsApp收件人配置
    @classmethod
    def get_whatsapp_recipients(cls):
        recipients = os.getenv('WHATSAPP_RECIPIENTS', '')
        return [
            r.strip() if r.strip().startswith('whatsapp:') else f'whatsapp:{r.strip()}'
            for r in recipients.split(',') if r.strip()
        ]
    
    # 邮件收件人配置
    @classmethod
    def get_email_recipients(cls):
        recipients = os.getenv('EMAIL_RECIPIENTS', '')
        return [r.strip() for r in recipients.split(',') if r.strip()] 