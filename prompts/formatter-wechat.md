# 微信公众号 (WeChat Official Account) Format Adapter

Transform the refined draft into a version optimized for publishing on WeChat Official Account (微信公众号).

## Adaptations

### WeChat Critical Constraints
- **NO external links**: WeChat blocks all external hyperlinks in articles. Replace every `[text](url)` with plain text. For important URLs, add them as a "阅读原文" (Read Original) link — WeChat allows exactly ONE external link via the "阅读原文" feature at the bottom.
- **Inline CSS only**: WeChat strips `<link>` tags and external stylesheets. All styling must be inline CSS on HTML elements.
- **Images must be on WeChat CDN**: External image URLs will be blocked. Flag all images with `<!-- UPLOAD TO WECHAT CDN: description -->` for manual upload.
- **No JavaScript**: WeChat strips all scripts.

### WeChat HTML Formatting
Output as styled HTML suitable for pasting into the WeChat editor. Use inline CSS for all styling:

```html
<!-- Article Title -->
<h1 style="font-size: 22px; font-weight: bold; color: #333; text-align: center; margin-bottom: 8px;">标题</h1>

<!-- Section Headers -->
<h2 style="font-size: 18px; font-weight: bold; color: #1a73e8; border-left: 4px solid #1a73e8; padding-left: 12px; margin: 24px 0 12px 0;">章节标题</h2>

<!-- Body Text -->
<p style="font-size: 16px; line-height: 1.8; color: #333; margin-bottom: 16px; text-align: justify;">正文内容</p>

<!-- Key Points / Highlights -->
<p style="font-size: 16px; line-height: 1.8; color: #c0392b; font-weight: bold;">重点内容用红色加粗</p>

<!-- Blockquotes / Callouts -->
<blockquote style="border-left: 4px solid #e0e0e0; padding: 12px 16px; margin: 16px 0; background: #f9f9f9; font-size: 15px; color: #666;">
引用或提示内容
</blockquote>

<!-- Code Blocks -->
<pre style="background: #f5f5f5; border-radius: 4px; padding: 16px; overflow-x: auto; font-size: 13px; line-height: 1.6;"><code style="font-family: 'Menlo', 'Consolas', monospace; color: #333;">代码内容</code></pre>

<!-- Inline Code -->
<code style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 14px; color: #c0392b;">inline code</code>
```

### Mobile-First Design
WeChat articles are read almost exclusively on mobile phones. Optimize for:
- Font size: body text at 16px minimum, never smaller than 14px
- Line height: 1.8 for body text (generous spacing for small screens)
- Short paragraphs: 2-3 sentences max per paragraph
- Wide margins on blockquotes and code for visual breathing room
- No tables wider than the viewport — convert to lists if needed
- Images should be full-width where possible

### Rich Text Emphasis
Use colored text for emphasis instead of just bold/italic:
- Key concepts: `<span style="color: #1a73e8; font-weight: bold;">关键概念</span>`
- Warnings: `<span style="color: #c0392b;">注意事项</span>`
- Success/positive: `<span style="color: #27ae60;">正面信息</span>`
- Use sparingly — max 2-3 colored highlights per section

### Image Handling
- Mark every image for WeChat CDN upload: `<!-- UPLOAD TO WECHAT CDN: [description] -->`
- Include a placeholder in the HTML: `<img style="max-width: 100%; margin: 16px 0;" src="WECHAT_CDN_PLACEHOLDER" alt="描述" />`
- Recommend image dimensions: width 900px (WeChat compresses automatically)
- Add image captions: `<p style="text-align: center; font-size: 13px; color: #999; margin-top: -8px;">图片说明</p>`

### QR Code CTA
End every article with a QR code call-to-action section:
```html
<div style="text-align: center; margin-top: 32px; padding: 24px; background: #f9f9f9; border-radius: 8px;">
  <p style="font-size: 16px; color: #333; font-weight: bold;">关注公众号，获取更多技术干货</p>
  <!-- UPLOAD TO WECHAT CDN: QR code image -->
  <img style="width: 200px; margin: 12px 0;" src="WECHAT_CDN_PLACEHOLDER" alt="公众号二维码" />
  <p style="font-size: 14px; color: #999;">扫码关注 · 一起进步</p>
</div>
```

### Content Requirements
- ALL content must be in Chinese (中文)
- Technical terms can remain in English but provide Chinese explanation on first use: `React (前端框架)`
- Code comments should be in Chinese where helpful
- Use Chinese punctuation: 。，、；：""''（）

### WeChat Platform Gotchas and Limits
- **Title**: max 64 Chinese characters. WeChat truncates at ~35 chars in the subscription list preview on mobile. Front-load the hook.
- **Abstract (摘要)**: max 120 Chinese characters. Shown in the subscription list below the title. This is your "ad copy" — make every character count.
- **External links**: COMPLETELY BLOCKED in article body. The ONLY external link allowed is the "阅读原文" (Read Original) button at the bottom. Use this for your most important link (usually the article's canonical URL or a GitHub repo).
- **Internal links**: you CAN link to other articles within the SAME WeChat Official Account. Use this for series navigation and cross-promotion.
- **Article length**: WeChat does not enforce a hard limit, but the reading experience degrades significantly past 5000 Chinese characters. Readers are on mobile and will abandon long articles. Aim for 2000-4000 characters.
- **Images**:
  - ALL images must be uploaded to WeChat's CDN via the editor. External image URLs are BLOCKED.
  - Max file size: 10MB per image
  - Recommended width: 900px (WeChat auto-compresses and resizes)
  - GIFs are supported but keep under 2MB for smooth loading on mobile data
  - WeChat strips EXIF data from uploaded images
- **Code blocks**:
  - WeChat's editor has a built-in code block feature that is limited
  - For better formatting, use the inline CSS `<pre><code>` approach in the template above
  - Long code blocks: WeChat does NOT support horizontal scrolling well. Keep code lines under 60 characters or the code will wrap awkwardly.
  - Consider using code screenshots for complex examples (upload as images)
- **Inline CSS**:
  - WeChat strips ALL external stylesheets and `<style>` tags
  - Only inline `style=""` attributes on individual elements survive
  - Some CSS properties are partially supported or behave differently:
    - `position: fixed/sticky` does NOT work
    - `flexbox` has partial support
    - `grid` is NOT supported
    - `transform` and `animation` have very limited support
  - Fonts: WeChat uses the system font. Custom font imports are ignored.
- **Third-party editing tools**: Many authors use tools like 135editor (135编辑器), Xiumi (秀米), or Markdown Nice to convert Markdown to WeChat-compatible HTML. If using these, note it in the output so the author knows the workflow.
- **Publishing schedule**: WeChat allows subscription accounts to post once per day. Service accounts can post 4 times per month. Plan accordingly.
- **Distribution**: WeChat articles spread primarily through:
  - 朋友圈 (Moments) sharing — the article's cover image and title are critical here
  - 群聊 (Group chats) forwarding — the abstract is what people see before clicking
  - 搜一搜 (Search) — WeChat's built-in search indexes articles; optimize for Chinese keywords
- **Analytics**: WeChat provides detailed analytics (阅读量, 分享数, 收藏数). Track these to inform future article strategy.
- **Comments**: WeChat comments must be manually approved by the account admin. Prepare suggested reply templates for common questions.

## Language

This adapter ALWAYS outputs in Chinese regardless of the language directive. This is because WeChat Official Account content targets a Chinese-speaking audience.
- Article prose, section titles, analysis text -> Chinese (中文)
- Code, JSON keys, file names, technical terms -> English (with Chinese annotations)
- Chinese punctuation throughout

## Output

Write to `.essay-state/final-wechat.md`
