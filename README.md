# Makelaarsland House Alert System

这个系统可以自动处理 Makelaarsland 的新房提醒邮件，提取房屋信息，并生成一个包含所有相关信息的网页。

## 功能特点

1. 自动监控邮箱中的 Makelaarsland 新房提醒
2. 提取邮件中的房屋基本信息
3. 自动登录 Makelaarsland 网站获取详细信息
4. 使用 Google Maps API 计算到最近火车站的距离
5. 生成包含所有信息的网页
6. 通过 WhatsApp 发送通知

## 安装要求

- Python 3.8+
- Chrome 浏览器
- 各种 API 密钥和账户信息

## 安装步骤

1. 克隆仓库：
```bash
git clone [repository-url]
cd [repository-name]
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 创建 `.env` 文件并配置以下环境变量：
```
EMAIL=your-email@gmail.com
EMAIL_PASSWORD=your-email-password
MAKELAARSLAND_USERNAME=your-makelaarsland-username
MAKELAARSLAND_PASSWORD=your-makelaarsland-password
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number
WHATSAPP_NUMBER=your-whatsapp-number
```

## 使用方法

1. 确保所有环境变量都已正确配置
2. 运行主程序：
```bash
python main.py
```

3. 系统会自动：
   - 检查邮箱中的新邮件
   - 提取房屋信息
   - 获取详细信息
   - 生成网页
   - 发送 WhatsApp 通知

## 注意事项

- 确保您的邮箱允许 IMAP 访问
- 需要有效的 Google Maps API 密钥
- 需要 Twilio 账户用于发送 WhatsApp 消息
- 确保有稳定的网络连接

## 故障排除

如果遇到问题，请检查：
1. 环境变量是否正确配置
2. 网络连接是否正常
3. API 密钥是否有效
4. 邮箱设置是否正确

## 贡献

欢迎提交问题和改进建议！

## 许可证

MIT License 