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

### Liquid Tags for Embeds
Use dev.to liquid tags for rich embeds:
- GitHub repos: `{% github user/repo %}`
- GitHub issues/PRs: `{% github user/repo/issues/123 %}`
- CodePen: `{% codepen url %}`
- YouTube: `{% youtube video_id %}`
- Twitter/X: `{% embed https://twitter.com/... %}`
- Generic embeds: `{% embed url %}`
- Collapsible sections:
  ```
  {% details Summary text %}
  Hidden content here
  {% enddetails %}
  ```

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

## Language

Follow the language directive provided by the conductor. If writing in Chinese:
- Article prose, section titles, analysis text -> Chinese (中文)
- Code, JSON keys, file names, technical terms -> English
- Maintain the same quality standards regardless of language
- dev.to has a growing Chinese-language community

## Output

Write to `.essay-state/final-devto.md`
