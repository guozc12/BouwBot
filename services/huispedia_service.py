import re
from utils.logging_config import logger

class HuispediaService:
    def get_huispedia_url(self, address: str) -> str:
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
                logger.info(f"[Huispedia] 生成URL: {url}")
                return url
            else:
                logger.info(f"[Huispedia] 地址格式不正确: {address}")
                return ""
        except Exception as e:
            logger.error(f"[Huispedia] 生成URL时发生错误: {str(e)}")
            return "" 