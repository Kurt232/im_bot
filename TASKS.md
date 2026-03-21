# Tasks
- [x] 搭建项目基础结构：pyproject.toml、.gitignore、setup.sh
- [ ] 实现 IMAP IDLE 邮件监听：连接邮箱，实时接收新邮件
- [ ] 实现邮件解析：提取主题、正文、附件，转为任务描述
- [ ] 实现任务执行：收到邮件后调用 TASK_COMMAND 执行任务
- [ ] 实现 SMTP 回复：将任务结果通过邮件回复给发件人
- [ ] 支持文件附件回传：任务输出中的 FILE: 路径作为附件发送
- [ ] 编写 Dockerfile 和 compose.yml
- [ ] 编写 start.sh 入口脚本
- [ ] 编写 Quickstart 文档
