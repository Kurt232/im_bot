# Progress Log

## 搭建项目基础结构
- **Commit**: 9261240
- 创建了 `pyproject.toml`（hatchling + imapclient 依赖）、`.gitignore`（Python 项目标准）、更新了 `setup.sh`（uv venv + pip install）
- 采用 `src/im_bot_email/` layout，需要在 pyproject.toml 中配置 `tool.hatch.build.targets.wheel.packages`
- uv 安装验证通过

## 实现 IMAP IDLE 邮件监听
- **Commit**: cb7f8b7
- 新增 `config.py`（环境变量读取）和 `listener.py`（IDLE 监听主循环）
- imapclient 的 IDLE API：`idle()` 进入、`idle_check(timeout)` 等待响应、`idle_done()` 退出
- IDLE 需每 5 分钟续约一次，否则服务器可能断开；检测 `EXISTS` 响应来判断新邮件
- 使用 `unittest.mock` 测试 IMAP 交互，避免需要真实邮箱连接
- 环境中无 pip，需用 `uv pip install` 安装 pytest

## 实现邮件解析
- **Commit**: 37ed864
- 新增 `parser.py`：`ParsedEmail` 数据类 + `parse_email()` 函数
- 支持：纯文本/HTML 邮件、multipart（优先 text/plain，fallback text/html）、RFC 2047 编码头、多附件提取
- `to_task_description()` 方法将解析结果格式化为 TASK_COMMAND 的输入文本
- HTML→纯文本转换用正则剥离标签 + `html.unescape()`，足够应对常见邮件格式
- 13 个测试覆盖各种场景（纯文本、HTML、multipart、附件、编码头、空主题等）

## 实现任务执行
- **Commit**: e331cd5
- 新增 `executor.py`：`TaskResult` 数据类 + `execute_task()` 函数
- 通过 `subprocess.run(shell=True)` 执行 `TASK_COMMAND`，将 `ParsedEmail.to_task_description()` 作为 stdin 传入
- 附件保存到临时目录，通过 `ATTACHMENTS_DIR` 环境变量传给命令
- 支持超时控制（`TASK_TIMEOUT` 环境变量，默认 300 秒），超时返回 rc=-1
- 8 个测试覆盖：stdin 传递、失败命令、stderr 捕获、附件保存、超时处理

## 实现 SMTP 回复
- **Commit**: 6468de2
- 新增 `replier.py`：`send_reply()` 函数，通过 SMTP_SSL 将 TaskResult 回复给原始发件人
- `_build_body()` 将 TaskResult 格式化为可读文本（[OK]/[FAIL] 状态 + stdout/stderr 分段）
- `_build_message()` 构建 MIMEText 回复，自动添加 `Re:` 前缀（避免重复）
- SMTP_HOST 为空时静默跳过，不抛异常（适配未配置 SMTP 的部署场景）
- 使用 `smtplib.SMTP_SSL`（隐式 TLS），对应标准 465 端口
- 10 个测试覆盖：body 格式化（成功/失败/双流/空输出）、消息头构建、空 host 跳过、SMTP 连接和发送验证

## 支持文件附件回传
- **Commit**: 2f885ac
- 在 `replier.py` 中新增 `extract_file_paths()` 从 stdout 提取 `FILE: /path` 行，`_strip_file_lines()` 从 body 中移除这些行
- 有附件时 `_build_message()` 返回 `MIMEMultipart`，无附件时仍返回 `MIMEText`，保持向后兼容
- 不存在的文件路径会 log warning 并跳过，不会导致发送失败
- 新增 10 个测试覆盖：路径提取（存在/不存在/多个/空）、行剥离、body 过滤、消息类型切换、端到端发送

## 编写 Dockerfile 和 compose.yml
- **Commit**: 50f4430
- 项目已有 `Dockerfile` 和 `compose.yml` 用于 Claude Code worker 开发环境，不能覆盖
- 创建 `Dockerfile.bot`（Python 3.12-slim + uv 多阶段拷贝）作为邮件机器人的部署镜像
- 在 `compose.yml` 中新增 `bot` 服务，使用 `dockerfile: Dockerfile.bot` 指定构建文件
- 同时新增 `__main__.py` 入口，将 listener→parser→executor→replier 串联为完整流程
- 运行命令：`docker compose up bot`（仅启动邮件机器人）
- **教训**：先检查现有文件再创建，避免覆盖已有基础设施

## 编写 Quickstart 文档
- **Commit**: 9388700
- 在 README.md 中新增 Quickstart 部分，涵盖：环境变量配置（.env 示例）、直接运行和 Docker 两种启动方式、测试验证步骤、自定义 TASK_COMMAND 的输入输出格式说明
- 作为 README 的一部分而非独立文件，降低维护成本
- 包含 Gmail App Password 和 QQ/163 授权码的提示，避免用户用错误密码尝试

## 编写 start-bot.sh 入口脚本
- **Commit**: e3d562e
- 创建 `start-bot.sh`（而非 `start.sh`，因为后者已用于 Claude Code worker）
- 功能：加载 `.env`、校验必需环境变量（`IMAP_HOST`/`EMAIL_USER`/`EMAIL_PASSWORD`）、支持直接运行和 `--docker` 两种模式
- 使用 `set -a` / `. .env` / `set +a` 加载 env 文件，比逐行 export 更简洁
- 使用 `${!var}` 间接引用批量校验变量，避免重复代码

## 实现 Outlook OAuth2 支持（IMAP）+ 传统 SMTP 发送
- **Commit**: 48a74bb
- **问题**：微软已禁用 Outlook.com 的基本认证（用户名+密码）用于 IMAP，必须使用 OAuth2
- **IMAP OAuth2**：通过 MSAL `PublicClientApplication` + device-code flow 实现，token 缓存到 `.token_cache.json`
- **SMTP 发送**：Outlook.com 个人账户的 SMTP AUTH（包括 XOAUTH2 和基本认证）可能被禁用（5.7.139 错误），最终使用应用密码通过传统 SMTP 发送
- **关键教训**：
  - `offline_access` 是 MSAL 自动添加的保留 scope，不能显式传入
  - 个人账户 IMAP scope 必须用 `outlook.office.com`（不是 `outlook.office365.com`）
  - Azure 应用必须启用 "Allow public client flows" 并添加 "Mobile and desktop applications" 平台
  - IMAP 和 SMTP 使用不同的认证方式（OAuth2 vs 应用密码）是可行的混合方案
  - `noreply`/`mailer-daemon` 等地址必须过滤，防止回复循环
  - SMTP 发送失败不应导致 IMAP 监听崩溃，需要 try/except 隔离
