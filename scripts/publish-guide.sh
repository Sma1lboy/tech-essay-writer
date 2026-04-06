#!/usr/bin/env bash
# Outputs step-by-step publishing instructions for a given platform
# Usage: bash scripts/publish-guide.sh <platform> [project_dir]
#        bash scripts/publish-guide.sh list
#        bash scripts/publish-guide.sh all [project_dir]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUPPORTED_PLATFORMS="medium devto hashnode wechat juejin"

usage() {
  echo "Usage: publish-guide.sh <platform|list|all> [project_dir]"
  echo ""
  echo "Supported platforms: $SUPPORTED_PLATFORMS"
  echo ""
  echo "Commands:"
  echo "  <platform>   Show publishing guide for a specific platform"
  echo "  list         List all supported platforms"
  echo "  all          Show guides for all platforms"
  exit 1
}

# --- Platform guide functions ---

guide_medium() {
  local project_dir="${1:-}"
  cat <<'GUIDE'
================================================================================
  MEDIUM — https://medium.com
================================================================================

--- PRE-PUBLISH CHECKLIST ---

  Formatting:
    [ ] Paragraphs are short (2-4 sentences) for Medium's reading experience
    [ ] Pull quotes use > blockquote syntax for standout lines
    [ ] Horizontal rules (---) used sparingly for section breaks
    [ ] Headings start at ## (title is entered separately)
    [ ] First paragraph works as preview (no images or code)
    [ ] Bullet/numbered lists used strategically

  Images:
    [ ] Featured/hero image is 1500x750 pixels (2:1 ratio)
    [ ] All images have descriptive alt text
    [ ] Images uploaded manually to Medium (no external hosting)

  Frontmatter / Metadata:
    [ ] Title prepared (entered in Medium editor)
    [ ] Subtitle prepared (max 140 characters)
    [ ] Kicker label prepared (short topic label shown above title)
    [ ] Up to 5 tags selected
    [ ] Canonical URL set if cross-posting

  Code:
    [ ] Short inline code uses backtick formatting
    [ ] Code blocks under 10 lines use fenced Markdown blocks
    [ ] Long code blocks (10+ lines) converted to GitHub Gist embeds

--- STEP-BY-STEP PUBLISHING ---

  1. Go to https://medium.com and log in
  2. Click "Write" (pencil icon) to open the editor
  3. Paste your article title as the main heading
  4. Add the subtitle in the subtitle field
  5. Set the kicker (topic label above title) in story settings
  6. Paste the article body — Medium auto-formats Markdown pasting
  7. Upload and position the featured image (drag to top)
  8. For code blocks 10+ lines, create GitHub Gists and embed the URLs
  9. Upload all inline images manually to Medium
  10. Add up to 5 tags in the tag field
  11. Set the canonical URL in story settings if cross-posting
  12. Preview the article on both desktop and mobile
  13. Click "Publish" (or schedule for later)

--- SEO TIPS ---

  - First 2 sentences are the "hook" visible in preview cards — make them compelling
  - Subtitle is used as meta description — include primary keyword
  - Tags directly influence discoverability — use popular, relevant tags
  - Medium has high domain authority — articles rank well on Google
  - Use the kicker to signal topic area (e.g., "AI Engineering")
  - Internal links to your other Medium stories boost engagement
  - Consistent publishing schedule improves follower growth

--- POST-PUBLISH CHECKLIST ---

  [ ] Share on Twitter/X with a compelling thread
  [ ] Share on LinkedIn with a professional summary
  [ ] Add cross-post links to dev.to, Hashnode, or personal blog
  [ ] Submit to relevant Medium publications for wider reach
  [ ] Set up Medium Stats to track views, reads, and read ratio
  [ ] Respond to early comments to boost engagement
  [ ] Pin the article to your Medium profile if it's a flagship piece
GUIDE

  if [ -n "$project_dir" ] && [ -f "$project_dir/.essay-state/final-medium.md" ]; then
    echo ""
    echo "  NOTE: Medium-formatted draft found at:"
    echo "    $project_dir/.essay-state/final-medium.md"
  fi
  echo ""
}

guide_devto() {
  local project_dir="${1:-}"
  cat <<'GUIDE'
================================================================================
  DEV.TO — https://dev.to
================================================================================

--- PRE-PUBLISH CHECKLIST ---

  Formatting:
    [ ] Headings start at ## (title is in frontmatter)
    [ ] Table of contents added for long articles using anchor links
    [ ] Key terms bolded on first introduction
    [ ] Paragraphs are concise — dev.to readers scan quickly
    [ ] Emoji in headings used sparingly for engagement

  Images:
    [ ] Cover image is 1000x420 pixels
    [ ] All images have descriptive alt text
    [ ] Images uploaded to dev.to CDN (no external hotlinking)

  Frontmatter (YAML):
    [ ] title: set (enclosed in quotes)
    [ ] published: set to false initially
    [ ] description: concise, max 100 words
    [ ] tags: max 4, lowercase, hyphens (e.g., javascript, web-dev)
    [ ] canonical_url: set if cross-posting
    [ ] cover_image: URL to uploaded cover image
    [ ] series: set if part of a series

  Code:
    [ ] Fenced code blocks have language identifiers (```javascript)
    [ ] File-specific code has filename comments (// filename: src/app.ts)

  Liquid Tags:
    [ ] GitHub repos embedded with {% github user/repo %}
    [ ] YouTube videos with {% youtube video_id %}
    [ ] Collapsible sections with {% details %} / {% enddetails %}

--- STEP-BY-STEP PUBLISHING ---

  1. Go to https://dev.to and log in
  2. Click "Create Post" in the top navigation
  3. Paste the full Markdown including YAML frontmatter
  4. Upload the cover image and set the URL in frontmatter
  5. Upload any inline images via the editor's image upload
  6. Replace external embeds with dev.to liquid tags
  7. Verify tags are valid (check dev.to tag suggestions)
  8. Set published: false to save as draft first
  9. Preview using the "Preview" tab in the editor
  10. Check rendering of code blocks, images, and embeds
  11. Set published: true when ready
  12. Click "Publish"

--- SEO TIPS ---

  - Description field is used as meta description — include keywords
  - Tags are indexed by search engines — choose popular, relevant ones
  - dev.to has strong SEO — articles often rank on first page of Google
  - Use canonical_url to avoid duplicate content penalties when cross-posting
  - Title should be under 60 characters for full display in search results
  - First 100 characters of description appear in social cards
  - Consistent posting builds followers and improves feed visibility

--- POST-PUBLISH CHECKLIST ---

  [ ] Share on Twitter/X with article link and summary
  [ ] Share on LinkedIn
  [ ] Cross-post link back to original if published elsewhere first
  [ ] Add to a dev.to Series if part of a multi-part series
  [ ] Monitor comments and respond promptly (dev.to values discussion)
  [ ] Check dev.to analytics dashboard for views and reactions
  [ ] Submit to dev.to organizations if applicable
  [ ] Add "Connect with me" links in your dev.to profile
GUIDE

  if [ -n "$project_dir" ] && [ -f "$project_dir/.essay-state/final-devto.md" ]; then
    echo ""
    echo "  NOTE: dev.to-formatted draft found at:"
    echo "    $project_dir/.essay-state/final-devto.md"
  fi
  echo ""
}

guide_hashnode() {
  local project_dir="${1:-}"
  cat <<'GUIDE'
================================================================================
  HASHNODE — https://hashnode.com
================================================================================

--- PRE-PUBLISH CHECKLIST ---

  Formatting:
    [ ] Headings use consistent hierarchy (## main, ### sub)
    [ ] No skipped heading levels (e.g., ## to ####)
    [ ] Heading text is concise (appears in sidebar ToC)
    [ ] Blockquotes used for callouts (styled left border)
    [ ] Thematic breaks (---) between major sections

  Images:
    [ ] Cover image is 1600x840 pixels
    [ ] All images have descriptive alt text
    [ ] Images uploaded via Hashnode editor (auto-CDN)
    [ ] Descriptive filenames for uploaded images

  Frontmatter (YAML):
    [ ] title: set
    [ ] slug: URL-friendly, lowercase, hyphens only
    [ ] tags: up to 5, matching Hashnode popular tags
    [ ] cover: URL to cover image
    [ ] subtitle: compelling subtitle
    [ ] enableToc: true (for articles with 3+ sections)
    [ ] canonical: set if cross-posting

  Series:
    [ ] Series name noted if part of a series
    [ ] Series navigation context at top of article
    [ ] Links to previous/next articles included

  Code:
    [ ] Fenced code blocks with language identifiers
    [ ] Multi-file examples use bold labels before each block

--- STEP-BY-STEP PUBLISHING ---

  1. Go to https://hashnode.com and log in to your blog dashboard
  2. Click "Write an article" or "New Story"
  3. Paste the article content (Hashnode supports Markdown)
  4. Fill in the title, subtitle, and slug
  5. Upload and set the cover image
  6. Add up to 5 tags
  7. Set canonical URL if cross-posting
  8. Enable Table of Contents in article settings
  9. Assign to a series if applicable
  10. Preview the article
  11. Verify ToC renders correctly in sidebar
  12. Check code block syntax highlighting
  13. Add newsletter CTA near the end
  14. Click "Publish"

--- SEO TIPS ---

  - Hashnode blogs are hosted on your custom domain — great for personal SEO
  - Slug should contain primary keyword (auto-derived from title)
  - Tags help categorize on Hashnode's feed but also aid SEO
  - enableToc improves user engagement and time on page
  - Hashnode auto-generates Open Graph tags from your article metadata
  - Subtitle appears in social cards — make it compelling
  - Series boost internal linking and reader retention
  - Hashnode's built-in newsletter helps build an audience

--- POST-PUBLISH CHECKLIST ---

  [ ] Share on Twitter/X with article URL
  [ ] Share on LinkedIn
  [ ] Cross-post to dev.to with canonical_url pointing to Hashnode
  [ ] Enable newsletter subscription CTA
  [ ] Check Hashnode analytics for views and engagement
  [ ] Respond to comments and reactions
  [ ] Add to series if applicable
  [ ] Update your Hashnode blog's "About" page with latest article
GUIDE

  if [ -n "$project_dir" ] && [ -f "$project_dir/.essay-state/final-hashnode.md" ]; then
    echo ""
    echo "  NOTE: Hashnode-formatted draft found at:"
    echo "    $project_dir/.essay-state/final-hashnode.md"
  fi
  echo ""
}

guide_wechat() {
  local project_dir="${1:-}"
  cat <<'GUIDE'
================================================================================
  WECHAT OFFICIAL ACCOUNT (微信公众号) — https://mp.weixin.qq.com
================================================================================

--- PRE-PUBLISH CHECKLIST ---

  Formatting:
    [ ] Output is styled HTML with inline CSS (no external stylesheets)
    [ ] Font size: body text at 16px minimum, never smaller than 14px
    [ ] Line height: 1.8 for body text
    [ ] Paragraphs are 2-3 sentences max (mobile-first)
    [ ] Section headers use colored left border style
    [ ] Key concepts use colored text (<span style="color: #1a73e8;">)
    [ ] No JavaScript in the article (WeChat strips scripts)

  Images:
    [ ] ALL images uploaded to WeChat CDN (external URLs blocked)
    [ ] Image width: 900px recommended
    [ ] Image captions added below each image
    [ ] QR code image prepared for the CTA section

  Links:
    [ ] ALL external hyperlinks removed (WeChat blocks them)
    [ ] One external link saved for "阅读原文" (Read Original) slot
    [ ] Important URLs mentioned as plain text where needed

  Content:
    [ ] ALL content is in Chinese (中文)
    [ ] Technical terms have Chinese annotations on first use
    [ ] Chinese punctuation used throughout (。，、；：""''（）)
    [ ] Code comments in Chinese where helpful

  Code:
    [ ] Code blocks use <pre><code> with inline styling
    [ ] Font family set to monospace (Menlo, Consolas)
    [ ] Code font size: 13px with 1.6 line height
    [ ] Inline code styled with background color and padding

--- STEP-BY-STEP PUBLISHING ---

  1. Go to https://mp.weixin.qq.com and log in to your Official Account
  2. Navigate to "Content Management" (内容管理) > "New Article" (新建图文)
  3. Enter the article title in the title field
  4. Switch to the rich text / HTML editor mode
  5. Paste the styled HTML content
  6. Upload ALL images to WeChat's CDN via the image manager
  7. Replace image placeholders (WECHAT_CDN_PLACEHOLDER) with CDN URLs
  8. Upload the QR code image for the CTA section
  9. Set the cover image (封面图) — first image or custom thumbnail
  10. Set the "阅读原文" (Read Original) link if applicable
  11. Add the author name in the author field
  12. Preview on mobile using the WeChat preview scan feature
  13. Verify all images load correctly (CDN only)
  14. Verify no broken external links remain
  15. Send to a test group for final review
  16. Schedule or publish immediately

--- SEO TIPS ---

  - WeChat SEO is primarily internal (WeChat Search / 搜一搜)
  - Title should contain keywords for 搜一搜 discoverability
  - First 54 characters of title appear in push notifications — front-load keywords
  - Article abstract/digest (摘要) is crucial for share cards
  - Consistent publishing time builds reader habits
  - Tags/categories help WeChat's recommendation algorithm
  - High read completion rate signals quality to the algorithm
  - Encourage 在看 (Wow) reactions — they surface articles in friends' feeds

--- POST-PUBLISH CHECKLIST ---

  [ ] Share to WeChat Moments (朋友圈)
  [ ] Forward to relevant WeChat groups
  [ ] Cross-post link to Juejin, Zhihu, or personal blog
  [ ] Monitor read count (阅读量) in the backend dashboard
  [ ] Track 在看 (Wow) and share counts
  [ ] Respond to comments in the comment section
  [ ] Pin the article (置顶) if it's a flagship piece
  [ ] Add to article collection (合集) if part of a series
GUIDE

  if [ -n "$project_dir" ] && [ -f "$project_dir/.essay-state/final-wechat.md" ]; then
    echo ""
    echo "  NOTE: WeChat-formatted draft found at:"
    echo "    $project_dir/.essay-state/final-wechat.md"
  fi
  echo ""
}

guide_juejin() {
  local project_dir="${1:-}"
  cat <<'GUIDE'
================================================================================
  JUEJIN (掘金) — https://juejin.cn
================================================================================

--- PRE-PUBLISH CHECKLIST ---

  Formatting:
    [ ] Headings start at ## (title entered separately on Juejin)
    [ ] Admonition blocks used where supported (:::tip / :::warning)
    [ ] Fallback to styled blockquotes (> **提示**: ...) if unsure
    [ ] Tables used for comparisons (Juejin renders Markdown tables well)
    [ ] Horizontal rules (---) for major section breaks

  Images:
    [ ] Cover image (封面图) is 800x450 pixels
    [ ] Images flagged for Juejin CDN upload
    [ ] Image captions in italics below each image (*图：说明*)
    [ ] Cover image is compelling and relevant to the article

  Metadata:
    [ ] Category (分类) selected: 前端 | 后端 | Android | iOS | 人工智能 | 开发工具 | 代码人生 | 阅读
    [ ] Tags (标签): up to 10, using established Juejin tags
    [ ] Column (专栏) assigned if applicable

  Content:
    [ ] ALL content is in Chinese (中文)
    [ ] Technical terms in English where standard (React, Node.js, Docker)
    [ ] Chinese punctuation throughout (。，、；：""''（）)
    [ ] First paragraph is a strong hook (first ~100 chars are preview)
    [ ] Summary section (总结) at the end to encourage bookmarking

  Code:
    [ ] Fenced code blocks with language identifiers
    [ ] Syntax highlighting verified for all code blocks
    [ ] Code comments in Chinese where helpful

--- STEP-BY-STEP PUBLISHING ---

  1. Go to https://juejin.cn and log in
  2. Click the "+" or "创作" (Create) button
  3. Select "写文章" (Write Article)
  4. Enter the article title in the title field
  5. Paste the Markdown content into the editor
  6. Select the category (分类) from the dropdown
  7. Add up to 10 tags (标签) — use Juejin's tag suggestions
  8. Upload the cover image (封面图) — 800x450 recommended
  9. Upload inline images via the editor (auto-hosted on Juejin CDN)
  10. Assign to a column (专栏) if part of a series
  11. Add series navigation context at the top if applicable
  12. Preview the article in the editor
  13. Verify code syntax highlighting renders correctly
  14. Click "发布" (Publish)

--- SEO TIPS ---

  - Juejin articles rank well on Baidu and Google for Chinese tech queries
  - Title should contain primary Chinese keywords for Baidu SEO
  - First 100 characters serve as the preview — make them compelling
  - Tags directly affect discoverability in Juejin's feed algorithm
  - Category selection determines which feed your article appears in
  - High 点赞 (like) and 收藏 (bookmark) counts boost article ranking
  - Consistent posting schedule builds follower base
  - Column (专栏) series increase internal linking and retention

--- POST-PUBLISH CHECKLIST ---

  [ ] Share to WeChat groups and Moments (朋友圈)
  [ ] Cross-post to WeChat Official Account with canonical link
  [ ] Share on Zhihu if relevant
  [ ] Monitor 阅读量 (read count), 点赞 (likes), 收藏 (bookmarks)
  [ ] Respond to comments to boost engagement
  [ ] Add "觉得有用？点个赞吧！" CTA if not already in article
  [ ] Add to column (专栏) if part of a series
  [ ] Update 相关推荐 (Related Reading) section with links to new articles
GUIDE

  if [ -n "$project_dir" ] && [ -f "$project_dir/.essay-state/final-juejin.md" ]; then
    echo ""
    echo "  NOTE: Juejin-formatted draft found at:"
    echo "    $project_dir/.essay-state/final-juejin.md"
  fi
  echo ""
}

list_platforms() {
  echo "Supported publishing platforms:"
  echo ""
  echo "  medium     Medium (https://medium.com)"
  echo "  devto      dev.to (https://dev.to)"
  echo "  hashnode   Hashnode (https://hashnode.com)"
  echo "  wechat     WeChat Official Account / 微信公众号 (https://mp.weixin.qq.com)"
  echo "  juejin     Juejin / 掘金 (https://juejin.cn)"
  echo ""
  echo "Usage:"
  echo "  publish-guide.sh <platform> [project_dir]"
  echo "  publish-guide.sh all [project_dir]"
}

show_guide() {
  local platform="$1"
  local project_dir="${2:-}"
  case "$platform" in
    medium)   guide_medium "$project_dir" ;;
    devto)    guide_devto "$project_dir" ;;
    hashnode) guide_hashnode "$project_dir" ;;
    wechat)   guide_wechat "$project_dir" ;;
    juejin)   guide_juejin "$project_dir" ;;
    *)
      echo "Error: Unknown platform '$platform'" >&2
      echo "Supported platforms: $SUPPORTED_PLATFORMS" >&2
      exit 1
      ;;
  esac
}

# --- Main ---

COMMAND="${1:-}"

if [ -z "$COMMAND" ]; then
  usage
fi

case "$COMMAND" in
  list)
    list_platforms
    ;;
  all)
    PROJECT_DIR="${2:-}"
    for platform in $SUPPORTED_PLATFORMS; do
      show_guide "$platform" "$PROJECT_DIR"
    done
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    PROJECT_DIR="${2:-}"
    show_guide "$COMMAND" "$PROJECT_DIR"
    ;;
esac
