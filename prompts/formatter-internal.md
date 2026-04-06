# Internal Version Formatter

Transform the refined draft into a version optimized for company-internal publication.

## Adaptations

### Add Company Context
- Where the article discusses general patterns, add "How this applies to us" callouts
- Reference internal tools, systems, or processes where relevant
- Connect the article's insights to current team projects or challenges
- If the article recommends a tool or pattern, note whether the team already uses it, should adopt it, or has a reason not to

### Format for Internal Platforms
- Clean Markdown compatible with Confluence / Notion / internal wiki
- Add a TL;DR section at the top (3-5 bullet points)
- Include a "Discussion Questions" section at the end for team sync
- Add "Related Internal Resources" section linking to internal docs/repos

### Executive Summary

Every internal article MUST begin with a structured executive summary for leadership and time-pressed readers. This goes BEFORE the TL;DR:

```markdown
## Executive Summary

**What**: One sentence describing what this article covers.
**Why it matters**: One sentence on business/team impact.
**Key finding**: The single most important takeaway.
**Recommended action**: What should the team do as a result?
**Time to read**: ~X minutes
```

The executive summary is NOT the same as TL;DR. The executive summary frames business relevance and recommended actions. TL;DR summarizes the technical content.

### Action Items Section

End every internal article with a concrete action items section. This turns the article from "interesting read" into "operational input":

```markdown
## Action Items

### Immediate (This Sprint)
- [ ] [Specific action] — Owner: [role/team] [~effort estimate]
- [ ] [Specific action] — Owner: [role/team] [~effort estimate]

### Short-term (This Quarter)
- [ ] [Specific action] — Owner: [role/team]

### Exploration (Backlog)
- [ ] [Specific action] — Owner: [role/team]
```

Rules for action items:
- Every action item must be specific and assignable (not "think about X" but "evaluate X for our Y service and report findings")
- Assign to roles, not individuals (e.g., "Platform team", "Tech lead", "On-call engineer")
- Include a rough effort estimate where possible: `[~2h]`, `[~1 sprint]`, `[~1 day investigation]`
- If the article doesn't naturally produce action items, write: "No immediate action items — this article is for awareness and future reference"

### Company Publication Formatting Standards

Follow these standards for consistency across all internal publications:

**Document Structure (in order):**
1. Metadata header
2. Executive Summary
3. TL;DR (bullet points)
4. Article body (with "How this applies to us" callouts woven in)
5. Action Items
6. Discussion Questions
7. Related Internal Resources
8. Appendix (optional — raw data, extended code, reference links)

**Metadata Header:**
```markdown
---
author: [Author Name]
team: [Team Name]
date: [YYYY-MM-DD]
status: draft | review | published
tags: [internal tags for wiki search]
---
```

**Callout Blocks:**
- Internal relevance: `> **How this applies to us:** [context]`
- Warnings: `> **Internal Note:** [caveat specific to our stack]`
- All acronyms expanded on first use (even internal ones — new hires read these too)

### Platform-Specific Formatting Gotchas

**Confluence:**
- Confluence uses its own storage format — Markdown support requires a plugin or manual conversion
- Tables render differently than in standard Markdown — test table-heavy sections
- Code blocks: use `{code:language=javascript}` macro format if pasting into the native editor
- Collapsible sections use `{expand:title}` macro, not HTML `<details>` tags
- Max recommended page length: break articles over 3000 words into child pages with a parent overview
- Image attachments must be uploaded to Confluence — external URLs may be blocked by corporate firewalls

**Notion:**
- Notion supports Markdown paste but converts it to blocks — some formatting (nested lists, complex tables) may not survive
- Code blocks support language selection but the language tag is separate from the content
- Toggle headings (collapsible sections) are a Notion-native feature — use them for optional/advanced content
- Callout blocks (`> ` with emoji) are a better fit than blockquotes for tips and warnings
- Notion databases: if this article could be part of a knowledge base, suggest database properties (tags, status, team)

**飞书 (Feishu/Lark):**
- Supports Markdown paste with good fidelity
- Has native code blocks with syntax highlighting
- Use Feishu's "mention" feature to tag relevant team members in the Discussion Questions
- Feishu docs support embedded polls — suggest one for the discussion question

**企业微信 (WeCom):**
- WeCom articles follow the same constraints as WeChat Official Account articles (inline CSS, no external links)
- Keep articles shorter for WeCom — colleagues will read on mobile during commute
- Use WeCom's "微文档" (micro-doc) for longer technical content

**钉钉 (DingTalk):**
- DingTalk docs support basic Markdown
- Keep formatting simple — complex nesting and tables may not render correctly
- Use DingTalk's task assignment feature to create action items from the article's recommendations

### Character and Length Limits
- TL;DR: 5 bullet points max, each under 20 words
- Discussion Questions: 3-5 questions, each specific enough to generate a real answer (not "What do you think?")
- Total length: internal articles should be 20-30% shorter than external versions — colleagues' time is the scarcest resource

## Language

Follow the language directive provided by the conductor. If writing in Chinese:
- Article prose, section titles, analysis text → Chinese (中文)
- Code, JSON keys, file names, technical terms → English
- Maintain the same quality standards regardless of language
- Format for Chinese internal platforms: 企业微信 (WeCom), 飞书 (Feishu/Lark), 钉钉 (DingTalk)
- TL;DR and Discussion Questions sections should also be in Chinese

### Tone Adjustment
- More conversational — this is for colleagues, not strangers
- Can assume shared context about company tech stack
- Include "lessons for our team" framing
- Use "we" instead of "I" for recommendations — this is a team document now

## Output

Write to `.essay-state/final-internal.md`
