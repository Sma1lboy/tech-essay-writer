# Medium Format Adapter

Transform the refined draft into a version optimized for publishing on Medium.

## Adaptations

### Medium Frontmatter (Paste-Based)
Medium does not use file-based frontmatter. Instead, generate a metadata block at the top of the file as a reference for the author when pasting into Medium's editor:

```
<!-- Medium Publishing Metadata
Title: <article title>
Subtitle: <compelling subtitle, max 140 chars>
Kicker: <short topic label shown above title, e.g. "AI Engineering">
Tags: <up to 5 comma-separated tags>
Canonical URL: <original publication URL if cross-posting>
-->
```

### Image Handling
- Recommend a featured/hero image at 1500x750 pixels (2:1 ratio)
- Mark featured image placement with: `![Featured: description](IMAGE_URL "featured")`
- Inline images with descriptive captions using standard Markdown image syntax
- All images should have alt text for accessibility
- Flag any images that need to be uploaded manually to Medium

### Code Formatting
- Medium has limited native code syntax highlighting
- Short inline code: use backtick formatting
- For code blocks under 10 lines: use standard Markdown fenced code blocks
- For complex or long code blocks (10+ lines): add a comment suggesting a GitHub Gist embed
  ```
  <!-- Consider embedding as Gist for better formatting: https://gist.github.com/... -->
  ```

### Medium-Specific Formatting
- Use `---` horizontal rules sparingly for section breaks
- Keep paragraphs short (2-4 sentences) for Medium's reading experience
- Use pull quotes for key insights: prefix standout lines with `> `
- Add a "clap-worthy" hook in the first 2 sentences (visible in preview cards)
- Ensure the first paragraph works as the article preview (no images or code)
- Use bullet/numbered lists strategically — they render well on Medium

### Engagement Elements
- End with a clear call-to-action (follow, clap, comment)
- Include a "Further Reading" section with hyperlinks
- Add a brief author bio line at the end

## Language

Follow the language directive provided by the conductor. If writing in Chinese:
- Article prose, section titles, analysis text -> Chinese (中文)
- Code, JSON keys, file names, technical terms -> English
- Maintain the same quality standards regardless of language
- Medium supports Chinese content well; optimize for Chinese-reading audience

## Output

Write to `.essay-state/final-medium.md`
