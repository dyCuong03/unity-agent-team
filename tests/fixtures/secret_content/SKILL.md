---
name: secret_content
description: Skill fixture containing secret-like content for security testing. Should be flagged.
---

# Secret Content Skill

This skill contains patterns that look like secrets — should be detected:

API_KEY=sk-1234567890abcdef1234567890abcdef
OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890ABCDE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz123456
password = "SuperSecret123!"
secret = "my-hardcoded-secret-value"
bearer_token: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.fake"
ANTHROPIC_API_KEY=sk-ant-api03-AAABBBCCCDDDEEEFFFGGG1234567890
