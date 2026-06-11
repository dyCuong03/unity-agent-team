---
name: incompatible_platform
description: Skill fixture with platform metadata incompatible with Linux/WSL environments where the team runs.
platform: windows-only
requires: win32api
shell: powershell
unity_min_version: "2019.1"
---

# Incompatible Platform Skill

This skill requires Windows-only components and an old Unity version.

```powershell
# Windows-only path separator
$path = "C:\Users\Agent\skills"
[System.IO.Path]::Combine("C:\Unity", "skill.exe")
```
