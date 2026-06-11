---
name: bom_prefixed
description: Fixture for BOM stripping: frontmatter preceded by UTF-8 BOM byte as emitted by some Windows editors and auto-generated Tier 3 skill tools.
---

# BOM-Prefixed Skill

This file begins with a UTF-8 BOM (U+FEFF). The validator must strip it before parsing frontmatter.
