from twilio.rest import Client as TwilioClient
from utils.logging_config import logger
from models.house import HouseInfo

class WhatsAppService:
    def __init__(self, account_sid: str, auth_token: str, phone_number: str, recipients: list):
        self.client = TwilioClient(account_sid, auth_token)
        self.phone_number = phone_number
        self.recipients = recipients
    
    def send_house_info(self, house_info: HouseInfo) -> None:
        """发送房屋信息到WhatsApp"""
        logger.info("Starting WhatsApp message preparation...")
        try:
            # 准备消息内容
            message = f"🏠 New House Alert!\n\n"
            message += f"Title: {house_info.title}\n"
            message += f"Address: {house_info.address}\n"
            message += f"Price: {house_info.price}\n"
            message += f"Details: {house_info.size_rooms}\n"
            message += f"Agent: {house_info.agent}\n"
            
            if house_info.nearest_station:
                station_info = house_info.nearest_station
                message += f"\n🚉 Nearest Station: {station_info.name}\n"
                message += f"Distance: {station_info.walking_distance}\n"
                message += f"Walking Time: {station_info.walking_time}\n"
            
            message += f"\n🔗 View Details: {house_info.url}"
            
            logger.info(f"Message length: {len(message)} characters")
            
            # 发送消息给每个收件人
            for recipient in self.recipients:
                try:
                    logger.info(f"Sending message to: {recipient}")
                    message = self.client.messages.create(
                        body=message,
                        from_=f'whatsapp:{self.phone_number}',
                        to=recipient
                    )
                    logger.info(f"Message sent successfully")
                    logger.info(f"Message SID: {message.sid}")
                    logger.info(f"Message status: {message.status}")
                except Exception as e:
                    logger.error(f"Failed to send message to {recipient}: {str(e)}")
                    continue
                
        except Exception as e:
            logger.error(f"Error in WhatsApp message preparation: {str(e)}")
            raise 