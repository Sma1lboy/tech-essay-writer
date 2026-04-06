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

### Kicker Text Strategy

The kicker is the small text label shown ABOVE the title on Medium. It sets context before the reader sees the headline:

- Keep it to 2-3 words maximum (e.g., "System Design", "Frontend Performance", "DevOps War Story")
- Use it to signal the article's domain, not repeat the title
- If submitting to a publication, the kicker often matches the publication's section name
- Good kickers: "Production Lessons", "Deep Dive", "Case Study", "Architecture"
- Bad kickers: "My Thoughts On React" (too long), "Article" (useless), same text as the title
- Set the kicker in the metadata block and also in Medium's editor when publishing

### Image Handling
- Recommend a featured/hero image at 1500x750 pixels (2:1 ratio)
- Mark featured image placement with: `![Featured: description](IMAGE_URL "featured")`
- Inline images with descriptive captions using standard Markdown image syntax
- All images should have alt text for accessibility
- Flag any images that need to be uploaded manually to Medium
- Medium auto-centers images and adds a light caption style — use `*Caption text*` below images
- For side-by-side comparisons, Medium does NOT support image grids — use before/after with a horizontal rule separator

### Code Formatting
- Medium has limited native code syntax highlighting
- Short inline code: use backtick formatting
- For code blocks under 10 lines: use standard Markdown fenced code blocks
- For complex or long code blocks (10+ lines): add a comment suggesting a GitHub Gist embed
  ```
  <!-- Consider embedding as Gist for better formatting: https://gist.github.com/... -->
  ```

### GitHub Gist Embed Best Practices

Gist embeds are the preferred way to show code on Medium, since Medium has no native syntax highlighting:

1. **When to use Gists**: any code block over 8 lines, any code that benefits from syntax highlighting, any code the reader might want to copy
2. **Gist formatting**: use a descriptive filename (e.g., `conductor.ts` not `code.ts`), include a brief comment at the top explaining what the code does
3. **Embed syntax**: paste the raw Gist URL on its own line — Medium auto-renders it with full highlighting
   ```
   https://gist.github.com/username/abc123
   ```
4. **Fallback**: always include the code as a fenced Markdown code block BELOW the Gist embed comment, so the source file is still readable without the Gist
5. **Multi-file Gists**: group related files into one Gist — Medium renders multi-file Gists with a tab interface
6. **In the generated output**: mark Gist opportunities with:
   ```
   <!-- GIST EMBED: [description] — create Gist from the code block below -->
   ```

### Pull Quotes

Pull quotes are a key Medium formatting tool for visual rhythm and emphasis:

- Use blockquote syntax (`> `) for pull quotes — Medium renders these with a large, styled left-border format
- Place a pull quote every 3-5 paragraphs to break up long text sections and create visual anchors
- The pull quote should be a memorable, self-contained insight — not just a repeated sentence from the previous paragraph
- Good pull quotes: surprising conclusions, counterintuitive observations, quotable one-liners
- Bad pull quotes: setup sentences that need context, generic statements, references to code
- Bold within a pull quote (`> **text**`) adds extra emphasis — use sparingly since the quote styling already draws attention
- Pull quotes work as "scannable anchors" — a reader skimming the article should get the gist from pull quotes alone

### Medium-Specific Formatting
- Use `---` horizontal rules sparingly for section breaks
- Keep paragraphs short (2-4 sentences) for Medium's reading experience
- Add a "clap-worthy" hook in the first 2 sentences (visible in preview cards)
- Ensure the first paragraph works as the article preview (no images or code)
- Use bullet/numbered lists strategically — they render well on Medium
- Medium strips most HTML — do NOT rely on inline HTML for formatting
- Subheadings (`##`) create visual breaks — use them every 3-5 paragraphs
- Medium does NOT support footnotes, tables, or task lists — convert these to prose or lists
- Bold and italic render well; strikethrough (`~~text~~`) does NOT work on Medium

### Engagement Elements
- End with a clear call-to-action (follow, clap, comment)
- Include a "Further Reading" section with hyperlinks
- Add a brief author bio line at the end

### Medium Platform Gotchas and Limits
- **Title**: no hard character limit but Medium truncates titles in feed cards around 80-100 chars. Keep titles under 80 chars for full visibility.
- **Subtitle**: max 140 characters. Appears below the title in the article and in some feed placements. Use it to complement the title, not repeat it.
- **Kicker**: the small text above the title (e.g., "AI Engineering"). Keep to 2-3 words. This helps with categorization and visual hierarchy.
- **Tags**: max 5 per article. Medium tags are curated — use existing popular tags. Top tech tags include: Programming, JavaScript, Python, Software Engineering, Machine Learning, Web Development, DevOps, React. Misspelled or niche tags get zero distribution.
- **Reading time**: auto-calculated at ~265 words/minute. Displayed prominently. Articles over 10 minutes see lower completion rates on Medium. Sweet spot is 5-8 minutes.
- **Code formatting limitations**: THIS IS THE BIGGEST PAIN POINT.
  - Medium has NO native syntax highlighting. Code blocks render as monospace text with a gray background.
  - For code-heavy articles, embed GitHub Gists (they render with full syntax highlighting).
  - Inline code uses backticks and renders with a subtle background.
  - Medium's paste-from-IDE feature sometimes preserves formatting, sometimes doesn't. Gists are the reliable option.
  - Code blocks cannot have filenames or language labels.
  - Very long code blocks get a scroll container on mobile that is awkward to navigate.
- **Image handling**:
  - Featured image: recommended 1500x750 (2:1 ratio) or 1400x1050 (4:3)
  - Medium auto-compresses images and serves via its CDN
  - GIFs autoplay but can be very heavy — keep under 5MB
  - Image captions: add using Medium's caption feature (not Markdown)
  - Alt text: Medium supports alt text but it is often hidden in the editor — always include it in the Markdown source
- **Publications**: submitting to a publication (e.g., Better Programming, Towards Data Science) dramatically increases reach. Note recommended publications in the metadata block.
- **SEO**: Medium passes significant domain authority. Articles on Medium often rank well on Google even for competitive terms. Optimize the title and first paragraph for search.
- **Paywall**: Medium's Partner Program puts articles behind the paywall. Decide before publishing: paywalled (earn money, less reach) or free (more reach, no earnings). Note this in metadata.
- **Canonical URL**: set via Medium's import tool or in article settings. CRITICAL when cross-posting to avoid Google deduplication penalties.
- **HTML stripping**: Medium strips most HTML when pasting. Do not rely on custom HTML. Stick to standard Markdown.
- **Link handling**: Medium converts links to "cards" when a URL is on its own line. This can be useful for linking to GitHub repos but takes up significant vertical space.
- **Newsletter**: Medium has built-in email subscriptions. Followers get notified of new posts.

## Language

Follow the language directive provided by the conductor. If writing in Chinese:
- Article prose, section titles, analysis text -> Chinese (中文)
- Code, JSON keys, file names, technical terms -> English
- Maintain the same quality standards regardless of language
- Medium supports Chinese content well; optimize for Chinese-reading audience

## Output

Write to `.essay-state/final-medium.md`
