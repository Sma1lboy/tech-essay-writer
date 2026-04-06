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

## Language

This adapter ALWAYS outputs in Chinese regardless of the language directive. This is because 掘金 content targets a Chinese-speaking developer audience.
- Article prose, section titles, analysis text -> Chinese (中文)
- Code, JSON keys, file names, technical terms -> English
- Chinese punctuation throughout

## Output

Write to `.essay-state/final-juejin.md`
