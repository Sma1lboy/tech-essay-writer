# dev.to Format Adapter

Transform the refined draft into a version optimized for publishing on dev.to.

## Adaptations

### dev.to Liquid Tag Frontmatter
Generate proper dev.to frontmatter at the top of the file:

```yaml
---
title: "<article title>"
published: false
description: "<concise description, max 100 words>"
tags: tag1, tag2, tag3, tag4
canonical_url: <original URL if cross-posting>
cover_image: <URL to cover image, recommended 1000x420>
series: "<series name if part of a series>"
---
```

- Tags: max 4, lowercase, no spaces (use hyphens), must be from dev.to's tag list when possible
- Description: shown in article cards and SEO; keep it compelling and under 100 words

### Code Formatting
- Use fenced code blocks with language tags for syntax highlighting:
  ````
  ```javascript
  // code here
  ```
  ````
- dev.to supports most language identifiers (javascript, python, ruby, go, rust, typescript, etc.)
- For file-specific code, add a filename comment: `// filename: src/agent.ts`

### Liquid Tags Reference (Complete)

dev.to uses Liquid tags for rich embeds and interactive elements. Use these instead of raw URLs or HTML:

**Content Embeds:**
- GitHub repos: `{% github user/repo %}`
- GitHub issues/PRs: `{% github user/repo/issues/123 %}`
- GitHub gists: `{% gist user/gist_id %}`  (renders with syntax highlighting)
- CodePen: `{% codepen https://codepen.io/user/pen/id %}`
- CodeSandbox: `{% codesandbox sandbox_id %}`
- StackBlitz: `{% stackblitz project_id %}`
- Replit: `{% replit @user/repl-name %}`

**Media Embeds:**
- YouTube: `{% youtube video_id %}`  (just the ID, not the full URL)
- Vimeo: `{% vimeo video_id %}`
- Twitter/X: `{% embed https://twitter.com/user/status/id %}`
- Generic embeds: `{% embed url %}`

**Interactive Elements:**
- Collapsible sections:
  ```
  {% details Summary text %}
  Hidden content here
  {% enddetails %}
  ```
- Table of contents: `{% toc %}` (auto-generates from headings)
- Comments/notes visible only in Markdown source: `{% comment %} ... {% endcomment %}`

**Usage Rules:**
- Liquid tags must be on their own line (no inline usage)
- Do not nest Liquid tags inside code blocks — they will be interpreted
- To display a Liquid tag as literal text, use `{% raw %}{% tag %}{% endraw %}`

### Image Handling
- All images must have descriptive alt text: `![Descriptive alt text](url)`
- Cover image should be 1000x420 pixels
- Use relative image descriptions that make sense without seeing the image
- Flag images that need to be uploaded to dev.to's CDN

### dev.to-Specific Formatting
- Use heading levels starting at `##` (the title is already `#`)
- Add a table of contents for long articles using anchor links
- Use `**bold**` for key terms on first introduction
- Emoji in headings can boost engagement on dev.to (use sparingly)
- Keep paragraphs concise — dev.to readers scan

### Engagement Elements
- End with a discussion prompt to encourage comments
- Include "Connect with me" links
- Add relevant series link if applicable
- Consider a "What's Next" section for follow-up articles

### dev.to Platform Gotchas and Limits
- **Title**: max 128 characters, but titles over 70 chars get truncated in feed cards
- **Description**: max 100 words; shown in article cards and social shares
- **Tags**: exactly 4 max, lowercase only, hyphens for multi-word (e.g., `web-development`). Invalid tags are silently dropped.
- **Cover image**: 1000x420px recommended. Images wider than 1000px are auto-resized. GIFs work but increase load time significantly.
- **Reading time**: auto-calculated by dev.to based on word count (~265 wpm). Articles over 8 min reading time see lower completion rates.
- **Markdown flavor**: dev.to uses a custom Markdown parser. Key differences from standard GFM:
  - Footnotes are NOT supported
  - `<details>/<summary>` HTML tags work but `{% details %}` liquid tags are preferred
  - Tables work but render poorly on mobile — keep to 3-4 columns max
  - LaTeX/math is NOT natively supported
- **Canonical URL**: if cross-posting, ALWAYS set `canonical_url` in frontmatter to avoid Google duplicate content penalties
- **Draft vs Published**: always set `published: false` in the generated file so the author can review before publishing
- **Series**: series name must match exactly across all articles in the series (case-sensitive)
- **Reaction types**: dev.to has heart, unicorn, bookmark, and "mind blown" reactions. Write content that earns bookmarks (practical/reference content) or unicorns (impressive/novel content).
- **Community guidelines**: dev.to moderators may flag self-promotional content. Ensure the article provides genuine educational value before any CTAs.

## Language

Follow the language directive provided by the conductor. If writing in Chinese:
- Article prose, section titles, analysis text -> Chinese (中文)
- Code, JSON keys, file names, technical terms -> English
- Maintain the same quality standards regardless of language
- dev.to has a growing Chinese-language community

## Output

Write to `.essay-state/final-devto.md`
