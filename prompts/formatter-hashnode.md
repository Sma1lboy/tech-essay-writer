# Hashnode Format Adapter

Transform the refined draft into a version optimized for publishing on Hashnode.

## Adaptations

### Hashnode YAML Frontmatter
Generate proper Hashnode frontmatter at the top of the file:

```yaml
---
title: "<article title>"
slug: "<url-friendly-slug>"
canonical: <original URL if cross-posting>
tags: [tag1, tag2, tag3, tag4, tag5]
cover: <URL to cover image>
subtitle: "<subtitle shown below title>"
enableToc: true
---
```

- Slug: lowercase, hyphens, no special chars — derived from the title
- Tags: up to 5, should match Hashnode's popular tag names when possible
- Cover: recommended dimensions 1600x840
- enableToc: set to true for articles with 3+ sections

### Code Formatting
- Use fenced code blocks with language identifiers for full syntax highlighting:
  ````
  ```typescript
  // Hashnode renders this with syntax highlighting
  ```
  ````
- Hashnode supports all major languages and renders code beautifully
- For multi-file examples, use a heading or bold label before each block:
  ```
  **`src/conductor.ts`**
  ```typescript
  // code
  ```
  ```

### Series Support
- If the article is part of a series, note in the frontmatter metadata block:
  ```
  <!-- Hashnode Series: "Series Name" — assign in Hashnode editor -->
  ```
- Add series navigation context at the top: "This is Part N of the [Series Name] series."
- Link to previous/next articles in the series if known

### Table of Contents
- Hashnode auto-generates ToC from headings when `enableToc: true`
- Use consistent heading hierarchy (`##` for main sections, `###` for subsections)
- Keep heading text concise — it appears in the sidebar ToC
- Avoid skipping heading levels

### Newsletter CTA
- Hashnode has built-in newsletter subscription
- Add a newsletter CTA near the end:
  ```
  ---
  *If you found this useful, subscribe to my Hashnode newsletter for more articles on [topic].*
  ```
- Reference the author's Hashnode blog URL

### Image Handling
- All images need alt text: `![Descriptive alt text](url)`
- Cover image recommended at 1600x840
- Hashnode CDN handles image optimization automatically
- Use descriptive filenames for uploaded images

### Hashnode-Specific Formatting
- Headings start at `##` (title is separate)
- Supports standard Markdown plus some extensions
- Blockquotes render with a styled left border — use for callouts
- Supports embedded tweets, YouTube, CodePen via URL pasting
- Use `---` for thematic breaks between major sections

### Engagement Elements
- End with a discussion prompt
- Add "Follow me on Hashnode" CTA
- Include relevant cross-links to other articles
- Encourage reactions (Hashnode has emoji reactions)

## Language

Follow the language directive provided by the conductor. If writing in Chinese:
- Article prose, section titles, analysis text -> Chinese (中文)
- Code, JSON keys, file names, technical terms -> English
- Maintain the same quality standards regardless of language
- Hashnode supports multilingual content

## Output

Write to `.essay-state/final-hashnode.md`
