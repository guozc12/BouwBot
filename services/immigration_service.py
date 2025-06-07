import requests
from bs4 import BeautifulSoup
from utils.logging_config import logger

class ImmigrationService:
    def get_immigration_index(self, postcode: str) -> str:
        """
        从 allochtonenmeter.nl 获取移民指数数据
        :param postcode: 邮编前4位数字
        :return: 移民指数数据HTML字符串
        """
        try:
            logger.info(f"[Immigration] 获取邮编 {postcode} 的移民数据...")
            url = f"http://www.allochtonenmeter.nl/?postcode={postcode}"
            response = requests.get(url)
            response.raise_for_status()
            
            logger.info("[Immigration] 解析页面内容...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找结果表格
            table = soup.find('table')
            if table:
                logger.info("[Immigration] 找到数据表格，开始提取...")
                # 提取表格数据并重新格式化
                rows = table.find_all('tr')
                logger.info(f"[Immigration] 找到 {len(rows)} 行数据")
                
                immigration_html = "<table style='width:100%;border-collapse:collapse;'>"
                for i, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        logger.info(f"[Immigration] 处理第 {i+1} 行，包含 {len(cells)} 个单元格")
                        immigration_html += "<tr>"
                        for cell in cells:
                            cell_text = cell.get_text(strip=True)
                            logger.info(f"[Immigration] 单元格内容: {cell_text}")
                            immigration_html += f"<td>{cell_text}</td>"
                        immigration_html += "</tr>"
                immigration_html += "</table>"
                logger.info("[Immigration] 表格数据提取完成")
                return immigration_html
            else:
                logger.info("[Immigration] 未找到数据表格")
                return "<p style='margin:0;color:#666;'>Geen immigratie informatie beschikbaar</p>"
                
        except Exception as e:
            logger.error(f"[Immigration] 发生错误: {str(e)}")
            logger.error(f"[Immigration] 错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"[Immigration] 错误堆栈: {traceback.format_exc()}")
            return "<p style='margin:0;color:#666;'>Geen immigratie informatie beschikbaar</p>" 