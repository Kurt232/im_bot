# CLAUDE.md

## Project: [Your Project Name]

### What is this?
[One paragraph describing the project and its purpose.]

### Tech Stack
- Language: Python 3.11+ / TypeScript
- Framework: [FastAPI / Next.js / etc.]
- Database: SQLite

### Your Workflow
1. Read tasks.md → pick the top unchecked task
2. Plan your approach (think before coding)
3. Implement with tests
4. Run tests: `python -m pytest` or `npm test`
5. Commit with a clear message
6. Update PROGRESS.md with lessons learned (see format below)
7. Mark the task done in tasks.md
8. Exit

### PROGRESS.md Format
每次完成任务或遇到问题后记录，**必须附上 git commit ID**：
- 遇到了什么问题
- 如何解决的
- 以后如何避免

**同样的问题不要犯两次！**

If running in a worktree, write to the main repo's PROGRESS.md via absolute path directly.

### Commit Format
`feat:`, `fix:`, `refactor:`, `docs:`, `test:`

### Rules
- NEVER delete existing working features
- NEVER modify CLAUDE.md without explicit human approval
- NEVER access files outside this project directory
- NEVER install system-level packages
- Always ensure the project runs after your changes
- One task = one commit
- If blocked, document in PROGRESS.md and move on

### Architecture
<!-- Update this section as the project grows -->

### Known Issues & Lessons
<!-- Append from PROGRESS.md reviews -->

### Sync Test
