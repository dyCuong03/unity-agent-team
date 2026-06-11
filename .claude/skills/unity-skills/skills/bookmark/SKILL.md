---
name: unity-bookmark
description: "Scene View bookmarks — save the current selection plus Scene View camera pivot/rotation/size under a name, jump back to it later, list, delete. Use when users want to save, recall, or manage scene viewpoints + selections in the editor. Triggers: bookmark, bookmarks, save view, goto view, jump to view, scene view, camera position, viewpoint, viewpoints, named view, selection snapshot, 书签, 视角, 保存视角, 视图书签, 跳转视角, 选中快照, 命名视角."
platforms: [unity-editor, claude-code]
task-categories: [editor-navigation, editor-automation]
use-when: |-
  Load when the task requires: Scene View bookmarks — save the current selection plus Scene View camera pivot/rotation/size under a name, jump back to it later, list, delete. Use when users want to save, recall, or manage scene viewpoints + selections in the editor. Unity Editor must be running with the unity-skills REST server reachable at http://localhost:8090.
do-not-use-when: |-
  Do not load when Unity Editor is not running locally. Do not load when unity-skills REST server is unreachable at http://localhost:8090. For workflow snapshots (object state undo) → use `workflow` module instead. For scene save/load → use `scene` module instead.
metadata:
  source: https://github.com/Besty0728/Unity-Skills
  version: 1.9.2
  tier: 2

---

# Bookmark Skills

Save and recall Scene View camera positions.

## Guardrails

**Operating Mode** (v1.9 three-tier):
- **Approval** (default): `bookmark_set` / `bookmark_goto` / `bookmark_list` 都标 `SkillMode.SemiAuto`，Approval 模式下可直接执行，无需走 grant 协议。与 `workflow` 模块文档保持一致（C# `WorkflowSkills.cs` 内三者均为 SemiAuto）。
- **Auto** / **Bypass**: SemiAuto and FullAuto run directly.
- Auto-forbidden in this module: `bookmark_delete` (`SkillOperation.Delete`). Reachable only under Bypass mode or via a user-managed Allowlist entry; the grant flow returns `MODE_FORBIDDEN`. Bookmarks themselves are in-memory only — `bookmark_delete` only removes the entry, no asset I/O.

**DO NOT** (common hallucinations):
- `bookmark_save` does not exist → use `bookmark_set`
- `bookmark_load` / `bookmark_restore` do not exist → use `bookmark_goto`
- `bookmark_remove` does not exist → use `bookmark_delete`
- Bookmarks save Scene View position + current selection, not scene state

**Routing**:
- For workflow snapshots (object state undo) → use `workflow` module
- For scene save/load → use `scene` module

## Skills

### `bookmark_set`
Save current Scene View camera position as a bookmark.
**Parameters:**
- `bookmarkName` (string): Bookmark name.

### `bookmark_goto`
Move Scene View camera to a saved bookmark.
**Parameters:**
- `bookmarkName` (string): Bookmark name.

### `bookmark_list`
List all saved bookmarks.
**Parameters:** None.

### `bookmark_delete`
Delete a saved bookmark.
**Parameters:**
- `bookmarkName` (string): Bookmark name.

## Exact Signatures

Exact names, parameters, defaults, and returns are defined by `GET /skills/schema` or `unity_skills.get_skill_schema()`, not by this file.
