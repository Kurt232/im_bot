# CLAUDE.md

### First Run
If README.md is empty, this is a new project. Run `./setup.sh` if needed, then:
1. Ask the user to describe the project
2. Write project description, tech stack, and architecture to README.md
3. Write initial tasks to tasks.md
4. Set up .gitignore based on the tech stack
5. Commit: `init: bootstrap project`

### Your Workflow
1. Read tasks.md → pick the top unchecked task
2. Plan your approach (think before coding)
3. Implement with tests if applicable
4. Commit with a clear message
5. Update PROGRESS.md with lessons learned (see format below)
6. Mark the task done in tasks.md
7. Exit

### PROGRESS.md Format
每次完成任务或遇到问题后记录，**必须附上 git commit ID**：
- 遇到了什么问题
- 如何解决的
- 以后如何避免

**同样的问题不要犯两次！**

If running in a worktree, write to the main repo's PROGRESS.md via:
```
git -C <main-repo-path> ...
```
or edit the file at its absolute path directly.

### Commit Format
`feat:`, `fix:`, `refactor:`, `docs:`, `test:`

### Rules
- NEVER delete existing working features
- NEVER modify CLAUDE.md without explicit human approval
- NEVER access files outside this repo
- NEVER install system-level packages
- Keep everything portable: no hardcoded absolute paths, no machine-specific assumptions
- One task = one commit
- If blocked, document in PROGRESS.md and move on
