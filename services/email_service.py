import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from utils.logging_config import logger
from models.house import HouseInfo

class EmailService:
    def __init__(self, email_address: str, email_password: str, recipients: list):
        self.email = email_address
        self.password = email_password
        self.recipients = recipients
    
    def _get_github_pages_url(self, house_info: HouseInfo) -> str:
        """从HouseInfo对象获取GitHub Pages URL"""
        return f"https://guozc12.github.io/makelaarsland-houses/{house_info.filename}"
    
    def send_house_info(self, house_info: HouseInfo) -> None:
        """发送房屋信息到邮件"""
        logger.info("Starting email message preparation...")
        try:
            # 准备邮件内容
            message = MIMEMultipart()
            message['From'] = self.email
            message['Subject'] = f"🏠 New House Alert: {house_info.title}"
            
            # 获取GitHub Pages URL
            github_pages_url = self._get_github_pages_url(house_info)
            
            # 构建HTML内容
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2c3e50;">🏠 New House Alert!</h2>
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #2c3e50; margin-top: 0;">{house_info.title}</h3>
                    <p><strong>Address:</strong> {house_info.address}</p>
                    <p><strong>Price:</strong> {house_info.price}</p>
                    <p><strong>Details:</strong> {house_info.size_rooms}</p>
                    <p><strong>Agent:</strong> {house_info.agent}</p>
            """
            
            if house_info.nearest_station:
                station_info = house_info.nearest_station
                html_content += f"""
                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 8px; margin-top: 15px;">
                        <h4 style="color: #2c3e50; margin-top: 0;">🚉 Nearest Station</h4>
                        <p><strong>Name:</strong> {station_info.name}</p>
                        <p><strong>Distance:</strong> {station_info.walking_distance}</p>
                        <p><strong>Walking Time:</strong> {station_info.walking_time}</p>
                    </div>
                """
            
            html_content += f"""
                    <p style="margin-top: 20px;">
                        <a href="{github_pages_url}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                            View Details
                        </a>
                    </p>
                </div>
            </body>
            </html>
            """
            
            message.attach(MIMEText(html_content, 'html'))
            
            # 发送邮件给每个收件人
            for recipient in self.recipients:
                try:
                    message['To'] = recipient
                    logger.info(f"Sending email to: {recipient}")
                    
                    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                        server.login(self.email, self.password)
                        server.send_message(message)
                    
                    logger.info(f"Email sent successfully to {recipient}")
                except Exception as e:
                    logger.error(f"Failed to send email to {recipient}: {str(e)}")
                    continue
                
        except Exception as e:
            logger.error(f"Error in email message preparation: {str(e)}")
            raise 