# BouwBot 🏠

一个智能房屋监控机器人，自动监控 Makelaarsland 的房源通知，提取详细信息并通过多种渠道发送通知。

## 功能特性

- 📧 **邮件监控**: 自动监控来自 Makelaarsland 的新房源邮件通知
- 🏡 **信息提取**: 自动提取房屋详细信息（价格、地址、面积、房间数等）
- 🗺️ **地理位置服务**: 
  - 查找最近火车站及步行时间
  - 计算到 Science Park 和 Flux 的通勤时间
- 💰 **WOZ 估值**: 自动获取房屋的 WOZ 估值信息
- 📊 **移民指数**: 根据邮编查询区域的移民指数
- 🔗 **Huispedia 链接**: 自动生成 Huispedia 房源链接
- 📱 **多渠道通知**: 
  - WhatsApp 消息通知（通过 Twilio）
  - 邮件通知
- 🌐 **自动发布**: 自动生成 HTML 页面并发布到 GitHub Pages

## 项目结构

```
BouwBot/
├── main.py                 # 主程序入口
├── core/                   # 核心功能模块
│   ├── email_handler.py    # 邮件处理
│   └── house_info.py       # 房屋信息处理
├── services/               # 服务模块
│   ├── email_service.py    # 邮件发送服务
│   ├── whatsapp_service.py # WhatsApp 发送服务
│   ├── maps_service.py     # Google Maps 服务
│   ├── woz_service.py      # WOZ 估值服务
│   ├── immigration_service.py  # 移民指数服务
│   └── huispedia_service.py    # Huispedia 服务
├── models/                 # 数据模型
│   └── house.py           # 房屋信息模型
├── utils/                  # 工具模块
│   ├── config.py          # 配置管理
│   └── logging_config.py  # 日志配置
├── makelaarsland-houses/   # GitHub Pages 子仓库
│   ├── index.html         # 主页
│   ├── house_*.html       # 房源详情页
│   └── houses.json        # 房源数据
└── publish_to_github.py    # GitHub Pages 发布脚本
```

## 安装与配置

### 1. 克隆仓库

```bash
git clone https://github.com/guozc12/BouwBot.git
cd BouwBot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件（参考 `.env.example`，如果存在）：

```env
# Email 配置
EMAIL=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Makelaarsland 配置
MAKELAARSLAND_USERNAME=your_username
MAKELAARSLAND_PASSWORD=your_password

# Google Maps API
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# Twilio 配置（WhatsApp）
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886

# 收件人配置
WHATSAPP_RECIPIENTS=whatsapp:+31612345678,whatsapp:+31687654321
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
```

### 4. 配置 GitHub Pages（可选）

如果需要自动发布到 GitHub Pages：

1. 在 `makelaarsland-houses` 目录中初始化 git 仓库
2. 配置远程仓库地址
3. 确保有推送权限

## 使用方法

### 运行主程序

```bash
python main.py
```

程序会：
1. 每 10 秒检查一次新邮件
2. 发现新房源时自动处理并发送通知
3. 自动发布到 GitHub Pages

### Windows 后台运行

使用 `run_forever.bat` 脚本在后台持续运行：

```bash
run_forever.bat
```

## 工作流程

1. **邮件监控**: 程序持续监控 Gmail 收件箱，查找来自 `info@makelaarsland.nl` 的未读邮件
2. **信息提取**: 从邮件 HTML 中提取房源基本信息（标题、地址、价格等）
3. **详细信息获取**: 
   - 登录 Makelaarsland 获取完整房源详情
   - 提取图片、详细信息、中介信息
4. **增强信息**: 
   - 查询最近火车站及通勤时间
   - 获取 WOZ 估值
   - 查询移民指数
   - 生成 Huispedia 链接
5. **通知发送**: 
   - 通过 WhatsApp 发送房源摘要
   - 通过邮件发送完整信息
6. **自动发布**: 生成 HTML 页面并推送到 GitHub Pages

## 依赖说明

- `selenium`: 用于自动化浏览器操作，获取 Makelaarsland 房源详情
- `beautifulsoup4`: HTML 解析
- `googlemaps`: Google Maps API 集成
- `twilio`: WhatsApp 消息发送
- `flask`: Web 服务（如需要）
- `python-dotenv`: 环境变量管理

## 注意事项

⚠️ **重要提示**:

- 确保 `.env` 文件已添加到 `.gitignore`，不要提交敏感信息
- Gmail 需要使用应用专用密码，不是普通密码
- Google Maps API 需要启用相关服务并设置配额限制
- Twilio 账户需要配置 WhatsApp Sandbox 或生产环境
- 确保有足够的 API 配额和权限

## 日志

程序运行日志保存在 `makelaarsland.log` 文件中，同时输出到控制台。

## 许可证

本项目为个人使用项目。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 作者

guozc12
