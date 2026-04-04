# Unity DOTS Agent Team — Setup

Add `/start-unity-dots-team` to your project so the 4-role Unity DOTS agent team is available as a slash command.

---

## 1. Enable Agent Team Mode

```sh
cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "preferences": {
    "tmuxSplitPanes": true,
    "autoBypassPermissions": true
  }
}
EOF
```

Restart Claude Code after writing this file.

---

## 2. Create the Command and Skill in Your Project

From your project root, create two files:

**`.claude/commands/start-unity-dots-team.md`** — copy from:
```
unity-agent-team/.claude/commands/team.md
```

**`.claude/skills/start-unity-dots-team/SKILL.md`** — copy from:
```
unity-agent-team/.claude/skills/start-unity-dots-team/SKILL.md
```

Both files reference all role configs and skills via `unity-agent-team/` paths. Do not copy or duplicate anything else from the package.

---

## 3. Use It

```sh
/start-unity-dots-team <task description>
```

The command spawns 4 agents in parallel — `architect`, `unity-dev`, `data-tool`, `tester` — each loading their role, skills, and rules from `unity-agent-team/`.
