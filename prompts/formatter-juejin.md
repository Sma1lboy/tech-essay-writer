# 掘金 (Juejin) Format Adapter

Transform the refined draft into a version optimized for publishing on 掘金 (Juejin).

## Adaptations

### Juejin Metadata Block
Generate a metadata reference block at the top of the file for the author to use when publishing:

```
<!-- 掘金发布设置
标题: <文章标题>
分类: <选择一个: 前端 | 后端 | Android | iOS | 人工智能 | 开发工具 | 代码人生 | 阅读>
标签: <最多10个标签, 逗号分隔>
封面图: <封面图片URL, 推荐尺寸 800x450>
专栏: <专栏名称, 如适用>
-->
```

- Category (分类): Choose the MOST relevant single category from the list above
- Tags (标签): Up to 10, use established Juejin tags when possible (e.g., JavaScript, React, Node.js, Go, Python, 架构, 性能优化, AI)
- Cover image (封面图): 800x450 recommended, eye-catching thumbnail

### Juejin Markdown Formatting
Juejin uses standard Markdown with full syntax highlighting support:
- Use fenced code blocks with language identifiers:
  ````
  ```typescript
  // 掘金支持完整的语法高亮
  ```
  ````
- Supports all major languages: javascript, typescript, python, go, java, rust, etc.
- Code blocks render with copy buttons automatically

### Column (专栏) Support
- If the article belongs to a series or column, note it in the metadata block
- Add series navigation at the top:
  ```
  > 本文是「系列名称」专栏的第 N 篇文章
  > 上一篇: [文章标题](链接)
  ```

### Juejin-Specific Formatting
- Headings start at `##` (title is entered separately on Juejin)
- Use `:::tip` / `:::warning` / `:::danger` admonition blocks if supported:
  ```
  ::: tip 提示
  这是一个提示内容
  :::
  ```
  If uncertain about support, fall back to styled blockquotes:
  ```
  > **提示**: 这是一个提示内容
  ```
- Use tables for comparisons — Juejin renders Markdown tables well
- Juejin supports image zoom — no need for thumbnail/full-size pairs
- Use `---` horizontal rules for major section breaks

### Image Handling
- Juejin has its own image CDN — images uploaded through the editor are auto-hosted
- Flag images for upload: `<!-- 上传至掘金: [图片描述] -->`
- Include placeholder: `![图片描述](JUEJIN_CDN_PLACEHOLDER)`
- Cover image should be compelling and relevant to the article topic
- Add captions below images in italics: `*图：说明文字*`

### Content Requirements
- ALL content must be in Chinese (中文)
- Technical terms can remain in English: `React`、`Node.js`、`Docker`
- Use Chinese punctuation throughout: 。，、；：""''（）
- Code comments in Chinese where helpful for reader understanding
- First paragraph should be a strong hook — Juejin shows first ~100 chars as preview

### Engagement Elements
- Juejin has a "点赞" (like) and "收藏" (bookmark) culture
- End with a summary section (总结) to encourage bookmarking
- Add "觉得有用？点个赞吧！" or similar CTA
- Include a brief author introduction
- Add "相关推荐" (Related Reading) section linking to other articles
- Encourage comments with a discussion question

### Juejin Platform Gotchas and Limits
- **Title**: max 100 Chinese characters. Titles over 50 chars get truncated in feed cards on mobile. Front-load the key information.
- **Category (分类)**: MUST select exactly one from the fixed list: 前端, 后端, Android, iOS, 人工智能, 开发工具, 代码人生, 阅读. Choosing the wrong category severely limits discovery.
- **Tags (标签)**: max 10 tags. Use established Juejin tags — check juejin.cn/tag for popular tags. Tags like "JavaScript", "React", "Node.js" have millions of followers. Custom tags get almost zero discovery.
- **Cover image (封面图)**: 800x450 recommended. Juejin auto-generates a placeholder if no cover is provided, but articles WITH custom covers get significantly more clicks in the feed.
- **First 100 characters**: Juejin shows the first ~100 chars as a preview in the feed. This is your "ad copy" — make it compelling. Do NOT start with "本文介绍..." or "大家好...".
- **Content moderation**: Juejin has strict content review. Articles may be delayed or rejected for:
  - Excessive self-promotion or marketing language
  - Content copied from other sources without attribution
  - Low-quality or AI-generated content (审核员 actively check for this)
  - External links to competing platforms may be flagged
- **Markdown support**:
  - Standard Markdown with syntax highlighting
  - Tables render well on desktop but poorly on mobile — keep to 3-4 columns max
  - Admonition blocks (`:::tip`, `:::warning`, `:::danger`) may or may not be supported depending on editor version — always provide a fallback styled blockquote
  - LaTeX math is supported via `$...$` (inline) and `$$...$$` (block)
  - Mermaid diagrams are supported in the new editor
- **Juejin Power Level (掘力值)**: articles from high-level authors get more visibility. New accounts should focus on quality over quantity to build credibility.
- **Draft saving**: Juejin auto-saves drafts. The generated file is a starting point — always review in Juejin's editor before publishing.
- **沸点 (Boiling Point)**: Juejin's short-form social feature. Consider publishing a 沸点 linking to the article for additional promotion.
- **Markdown Copy Issues**: when pasting Markdown into Juejin's editor, check that:
  - Code block language tags are preserved
  - Nested lists render correctly (Juejin sometimes flattens nested lists)
  - Image URLs are accessible from China (foreign CDNs may be slow or blocked)

## Language

This adapter ALWAYS outputs in Chinese regardless of the language directive. This is because 掘金 content targets a Chinese-speaking developer audience.
- Article prose, section titles, analysis text -> Chinese (中文)
- Code, JSON keys, file names, technical terms -> English
- Chinese punctuation throughout

## Output

Write to `.essay-state/final-juejin.md`
