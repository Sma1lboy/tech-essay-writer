# External Version Formatter

Transform the refined draft into a version optimized for public publication
to build the author's personal influence and reputation.

## Adaptations

### Remove Internal References
- Strip any company-specific tool names, internal URLs, or proprietary details
- Generalize company-specific examples into industry-relevant ones
- Ensure code examples are self-contained (no internal library dependencies)
- Search the draft for these red flags: internal domain names, Slack channel names, JIRA ticket IDs, internal wiki links, proprietary library imports

### Build Author Credibility
- Add an "About the Author" section at the end
- Weave in experience markers naturally ("In my 3 years building X...")
- Ensure the unique angle is front and center
- Include a specific, verifiable credential related to the article topic (not generic "experienced developer")

### Optimize for Public Platforms
- Clean Markdown compatible with dev.to, Medium, Hashnode, personal blog
- Include Open Graph metadata suggestions (title, description, image)
- Add canonical URL placeholder
- Include suggested tags for each platform

### Blog SEO Requirements

Optimize the article for search engine discovery:

**Title Tag Optimization:**
- Primary keyword within the first 60 characters
- Format: `[Primary Keyword]: [Benefit or Angle]` (e.g., "React Server Components: A Production Migration Guide")
- Avoid keyword stuffing — the title must read naturally

**Meta Description:**
- 150-160 characters, includes the primary keyword
- Frames the article as the answer to a search query
- Template: `Learn how to [action] with [technology]. [Specific result]. [What makes this guide different].`

**Heading Structure for SEO:**
- Exactly one `#` (H1) for the article title
- `##` (H2) for main sections — each should target a related keyword or question
- `###` (H3) for subsections — use for long-tail keyword variations
- Never skip heading levels (H2 to H4 is bad for SEO)
- At least one H2 should be phrased as a question readers might search for

**Content SEO Signals:**
- Primary keyword in: title, first paragraph, at least one H2, conclusion
- Use semantic variations (e.g., "React hooks" + "React custom hooks" + "useEffect patterns")
- 3-5 outbound links to authoritative sources
- Image alt text must be descriptive AND include relevant keywords
- Article length: 1500+ words for competitive keywords

### Social Preview Optimization

Optimize how the article appears when shared on social media:

**Open Graph Tags:**
```
og:title — max 60 chars, compelling, no truncation
og:description — max 200 chars, teaser not summary
og:image — 1200x630px, text readable at thumbnail size
og:type — "article"
og:url — canonical URL
```

**Twitter Card:**
```
twitter:card — "summary_large_image" for articles with hero images
twitter:title — max 70 chars
twitter:description — max 200 chars
twitter:image — 800x418 minimum
twitter:creator — author's Twitter handle
```

**Preview Checklist:**
- Does the og:image have readable text at thumbnail size (e.g., in a Slack message)?
- Does the og:title work WITHOUT the og:description? (some platforms only show the title)
- Test at: cards-dev.twitter.com/validator, developers.facebook.com/tools/debug/

### Canonical URL Handling

Manage canonical URLs to avoid duplicate content penalties:

- **Original publication**: canonical URL points to the author's own blog/site
- **Cross-posting**: every cross-posted version must include a canonical URL pointing back to the original
- **Per platform:**
  - dev.to: `canonical_url` in YAML frontmatter
  - Medium: set via "Import story" feature or story settings
  - Hashnode: `canonical` in YAML frontmatter
  - Personal blog: `<link rel="canonical" href="..." />` in HTML head
- **Timing**: publish on the original blog FIRST. Wait 24-48 hours for Google to index. Then cross-post.

### Cross-Platform Formatting Gotchas
Be aware of these platform-specific rendering differences that can break your article:

**Markdown Dialect Differences:**
- GitHub-Flavored Markdown (GFM) features like task lists (`- [ ]`), tables, and strikethrough (`~~text~~`) are NOT universally supported
- Some platforms strip HTML tags entirely (Medium), others allow inline HTML (dev.to, Hashnode)
- Footnote syntax (`[^1]`) is not supported on Medium or some blog engines

**Image Handling:**
- Always use absolute URLs for images, never relative paths
- Provide alt text for every image — some platforms use it as caption fallback
- Recommended image sizes vary: Medium (1500x750), dev.to (1000x420), Hashnode (1600x840)
- GIFs may not autoplay on all platforms

**Code Block Rendering:**
- Language identifiers after triple backticks: use lowercase (`typescript` not `TypeScript`)
- Some platforms don't support all language identifiers — fallback to closest match
- Long lines in code blocks cause horizontal scrolling on mobile — keep lines under 80 chars where possible
- Nested code blocks (code inside blockquotes) render inconsistently across platforms

**Character Limits to Respect:**
- Title: 100 chars max for universal compatibility (some platforms truncate earlier)
- Meta description: 155 chars for Google, 200 chars for social cards
- Alt text: 125 chars for accessibility tools
- URL slugs: keep under 60 chars

## Language

Follow the language directive provided by the conductor. If writing in Chinese:
- Article prose, section titles, analysis text → Chinese (中文)
- Code, JSON keys, file names, technical terms → English
- Maintain the same quality standards regardless of language
- Optimize for Chinese public platforms: 微信公众号, 知乎, 掘金, CSDN for articles
- Social package should produce Chinese-platform content instead of Twitter/LinkedIn/HN:
  - 微信公众号摘要 (WeChat article intro)
  - 微博推文 (Weibo post)
  - 知乎引流 (Zhihu answer hook)
  - 掘金摘要 (Juejin summary)

### Engagement Elements
- End with a clear call-to-action (follow, subscribe, try it)
- Include a "discussion prompt" that encourages comments — make it a genuine question, not "What do you think?"
- Add "Further Reading" section with external links (3-5 links, each with a one-sentence description of why it is worth reading)

## Output

Write to `.essay-state/final-external.md`

Also write social media package to `.essay-state/social-package.json` incorporating
the SEO reviewer's suggestions.
