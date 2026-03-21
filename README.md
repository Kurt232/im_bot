# IM Bot (Email)

邮件机器人 — 通过 IMAP IDLE 监听邮箱新邮件，解析为任务，执行后通过 SMTP 回复结果。无需公网服务器。

## 背景

基于 [消息通道集成可行性调研](../../docs/research-messaging-integration.md) 中的邮件方案，作为飞书机器人的备选通道。适用于团队不用飞书、需要最低技术门槛、可接受延迟的场景。

## 方案概述

### 接收消息

三种方式：

1. **IMAP 轮询 (Polling)** — 定时连接邮箱查询新邮件，简单可靠，延迟取决于轮询间隔（建议 30-60 秒）
2. **IMAP IDLE (推送)**（推荐） — RFC 2177 标准，服务器有新邮件时主动通知客户端，准实时，CPU 占用远低于轮询，需每 10 分钟续约一次 IDLE 命令
3. **Webhook** — Gmail API push notification（通过 Google Cloud Pub/Sub）、Microsoft Graph change notification

### 发送消息

- **SMTP**: 标准协议，所有邮箱都支持，Python `smtplib` 即可
- 支持富文本 HTML、附件、内嵌图片等

### 认证

| 方式 | 认证 |
|------|------|
| Gmail IMAP/SMTP | App Password |
| Outlook IMAP/SMTP | OAuth 2.0（XOAUTH2，基本认证已禁用） |
| QQ 邮箱 / 163 邮箱 | 授权码（非密码） |

### 频率限制

| 邮箱 | 发送限制 |
|------|----------|
| Gmail | 500 封/天（个人），2000 封/天（Workspace） |
| Outlook | 300 封/天 |
| QQ 邮箱 | 无明确公开限制，但有反垃圾机制 |

### 费用

**完全免费方案**: 个人 Gmail/QQ 邮箱 + Python 标准库

### 技术复杂度

**低** — 标准协议，生态极其成熟。Python 标准库即可完成收发。IMAP IDLE 实现稍复杂，但有成熟库。

### 限制和风险

- 邮件天然有延迟（非即时通讯）
- 反垃圾邮件机制可能导致回复被拦截（尤其发送频率高时）
- 邮件格式解析复杂（MIME、编码、HTML 等）
- 附件大小限制（通常 25MB）

## Quickstart

### 1. 配置环境变量

复制 `.env` 文件并填入邮箱信息：

```bash
cat > .env << 'EOF'
IMAP_HOST=imap.gmail.com
SMTP_HOST=smtp.gmail.com
EMAIL_USER=you@gmail.com
EMAIL_PASSWORD=your-app-password
TASK_COMMAND=echo
EOF
```

> **Gmail** 需要使用 [App Password](https://support.google.com/accounts/answer/185833)，不能用登录密码。
> **QQ 邮箱 / 163 邮箱** 使用授权码。

#### Outlook / Hotmail / Office 365（OAuth 2.0）

微软已全面禁用基本认证（用户名+密码），Outlook 邮箱**必须使用 OAuth 2.0**。

**第一步：注册 Azure 应用**

1. 登录 [Azure Portal → App registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. 点击 **New registration**
   - 名称：`Email Bot`（随意）
   - 账户类型：选 **Accounts in any organizational directory and personal Microsoft accounts**（必须包含个人账户）
   - 重定向 URI：选 **Mobile and desktop applications** → 填 `https://login.microsoftonline.com/common/oauth2/nativeclient`
3. 注册后，复制 **Application (client) ID**
4. 在左侧 **Authentication** → 底部 **Advanced settings** → **Allow public client flows** → 设为 **Yes** → Save
5. 在左侧 **API permissions** → **Add a permission** → **APIs my organization uses** → 搜索 `Office 365 Exchange Online` → **Delegated permissions** → 勾选：
   - `IMAP.AccessAsUser.All`
   - `SMTP.Send`
6. 点击 **Grant admin consent**（组织账户）或直接使用（个人账户会在首次登录时同意）

**第二步：配置 .env**

```bash
cat > .env << 'EOF'
IMAP_HOST=outlook.office365.com
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
EMAIL_USER=you@outlook.com
AUTH_METHOD=oauth2
OAUTH2_CLIENT_ID=your-azure-app-client-id
TASK_COMMAND=echo
EOF
```

> - 默认 `OAUTH2_TENANT_ID=common`，同时支持个人和组织账户，一般无需修改
> - 仅组织账户可填 `organizations` 或具体 Tenant ID
> - 首次启动时，程序会打印一个 URL 和验证码，在浏览器中完成授权后 token 会被缓存到 `.token_cache.json`，后续启动自动刷新，无需再次登录

**端口说明：** Outlook SMTP 使用 587 端口（STARTTLS），不同于 Gmail/QQ 的 465 端口（隐式 TLS）。程序会根据端口自动选择连接方式。

### 2a. 直接运行

```bash
./setup.sh                # 创建 venv，安装依赖
./start-bot.sh            # 启动邮件机器人
```

### 2b. Docker 运行

```bash
./start-bot.sh --docker   # 通过 docker compose 启动
```

或直接：

```bash
docker compose up bot
```

### 3. 测试

向 `EMAIL_USER` 邮箱发送一封邮件，机器人会自动执行 `TASK_COMMAND` 并将结果回复给你。

默认 `TASK_COMMAND=echo`，会原样回显邮件内容。替换为实际命令（如调用 Claude Code）即可处理真实任务。

### 自定义任务命令

`TASK_COMMAND` 接收邮件解析结果作为 stdin 输入，格式为：

```
Subject: 邮件主题
From: sender@example.com

邮件正文内容
```

如果邮件有附件，附件会保存到临时目录，路径通过 `ATTACHMENTS_DIR` 环境变量传入。

任务命令的 stdout 会作为回复正文。如果 stdout 中包含 `FILE: /path/to/file` 行，对应文件会作为附件发送。

## Architecture

```
用户 发邮件到 agent@example.com
    ↓
Agent 服务 (IMAP IDLE 监听)
    ├── 解析邮件内容为任务
    ├── 执行任务 (调用 Claude Code 等)
    └── SMTP 回复邮件（附结果）
```

## Tech Stack

- Python ≥ 3.10
- `imaplib` / `smtplib` — Python 标准库
- `imapclient` — 高级 IMAP 库（支持 IDLE）
- `msal` — Microsoft OAuth 2.0 认证库
- [uv](https://docs.astral.sh/uv/) — Python 包管理

## 环境变量

| 变量 | 说明 |
|---|---|
| `IMAP_HOST` | IMAP 服务器地址 |
| `IMAP_PORT` | IMAP 端口（默认 993） |
| `SMTP_HOST` | SMTP 服务器地址 |
| `SMTP_PORT` | SMTP 端口（默认 465；Outlook 用 587） |
| `EMAIL_USER` | 邮箱账号 |
| `EMAIL_PASSWORD` | 邮箱密码 / 授权码（`AUTH_METHOD=password` 时必填） |
| `AUTH_METHOD` | 认证方式：`password`（默认）或 `oauth2` |
| `OAUTH2_CLIENT_ID` | Azure 应用 Client ID（`AUTH_METHOD=oauth2` 时必填） |
| `OAUTH2_TENANT_ID` | Azure 租户（默认 `common`，支持个人+组织账户） |
| `OAUTH2_TOKEN_CACHE` | Token 缓存文件路径（默认 `.token_cache.json`） |
| `TASK_COMMAND` | 收到邮件后执行的命令（默认 `echo`） |
| `LOG_LEVEL` | 日志级别（默认 `INFO`） |
