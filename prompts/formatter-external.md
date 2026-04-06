# External Version Formatter

Transform the refined draft into a version optimized for public publication
to build the author's personal influence and reputation.

## Adaptations

### Remove Internal References
- Strip any company-specific tool names, internal URLs, or proprietary details
- Generalize company-specific examples into industry-relevant ones
- Ensure code examples are self-contained (no internal library dependencies)

### Build Author Credibility
- Add an "About the Author" section at the end
- Weave in experience markers naturally ("In my 3 years building X...")
- Ensure the unique angle is front and center

### Optimize for Public Platforms
- Clean Markdown compatible with dev.to, Medium, Hashnode, personal blog
- Include Open Graph metadata suggestions (title, description, image)
- Add canonical URL placeholder
- Include suggested tags for each platform

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
- Include a "discussion prompt" that encourages comments
- Add "Further Reading" section with external links

## Output

Write to `.essay-state/final-external.md`

Also write social media package to `.essay-state/social-package.json` incorporating
the SEO reviewer's suggestions.
