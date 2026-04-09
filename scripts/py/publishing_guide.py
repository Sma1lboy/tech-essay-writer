#!/usr/bin/env python3
"""Per-platform publishing workflow guide with SEO tips.
Usage: publishing_guide.py <platform> [project_dir] [--format json]
"""

import json
import os
import sys

from utils import read_json_file


VALID_PLATFORMS = ["internal", "external", "medium", "devto", "hashnode", "wechat", "juejin", "all"]
VALID_FORMATS = ["text", "json"]

GUIDES = {
    "internal": {
        "name": "Internal Company Publication",
        "steps": [
            "1. Verify final-internal.md is generated and reviewed",
            "2. Copy content into your company's publishing platform (Confluence, Notion, Google Docs, etc.)",
            "3. Add internal cross-references and team @mentions",
            "4. Tag relevant teams and projects",
            "5. Set appropriate access permissions (team/org/public)",
            "6. Add to relevant knowledge base or documentation hub",
            "7. Share link in team Slack/Teams channel",
            "8. Request peer review from 1-2 colleagues before finalizing",
        ],
        "seo_tips": [
            "Use clear, searchable titles (avoid clever puns for internal docs)",
            "Add a TL;DR section at the top for busy readers",
            "Tag with project names, team names, and technology keywords",
            "Include links to related internal documents and ADRs",
            "Add a 'Last updated' timestamp for freshness signals",
        ],
        "formatting": [
            "Markdown format with company template headers",
            "Include code blocks with syntax highlighting",
            "Use internal image hosting for diagrams",
            "Add table of contents for articles > 1500 words",
        ],
        "limits": {
            "title_max": "No strict limit (recommend < 80 chars)",
            "word_range": "500-5000 words typical",
        },
        "tags_advice": "Use project names, technology stack, and team identifiers",
        "checklist": [
            "Title is descriptive and searchable",
            "TL;DR or summary section present",
            "Code examples are tested and correct",
            "Internal links are valid",
            "Appropriate access permissions set",
            "Tagged with relevant project/team names",
        ],
    },
    "external": {
        "name": "External Blog / Company Engineering Blog",
        "steps": [
            "1. Verify final-external.md is generated and reviewed",
            "2. Run publish-check.sh to validate readiness",
            "3. Upload to your blog platform (WordPress, Ghost, Hugo, etc.)",
            "4. Add featured image and OpenGraph metadata",
            "5. Set canonical URL if cross-posting",
            "6. Preview and check formatting on desktop and mobile",
            "7. Schedule or publish",
            "8. Share social-package.json snippets on social media",
        ],
        "seo_tips": [
            "Title should include primary keyword within first 60 characters",
            "Meta description: 150-160 characters with call-to-action",
            "Use H2/H3 headings with keywords naturally included",
            "Add alt text to all images and diagrams",
            "Include 2-3 internal links and 2-3 external authoritative links",
            "Target 1500-2500 words for best SEO performance",
            "Add schema.org/Article JSON-LD structured data",
        ],
        "formatting": [
            "Markdown or HTML depending on platform",
            "Featured image: 1200x630px for social sharing",
            "Code blocks with language-specific syntax highlighting",
            "Author bio section at the end",
        ],
        "limits": {
            "title_max": "60 characters (SEO optimal)",
            "meta_description": "150-160 characters",
            "word_range": "1500-3000 words optimal for SEO",
        },
        "tags_advice": "3-5 technology-specific tags, include language/framework names",
        "checklist": [
            "Title is < 60 characters with primary keyword",
            "Meta description is 150-160 characters",
            "Featured/OG image is set (1200x630px)",
            "Canonical URL is configured",
            "Author bio is included",
            "Code examples are syntax-highlighted",
            "Mobile formatting verified",
            "Social sharing snippets prepared",
        ],
    },
    "medium": {
        "name": "Medium",
        "steps": [
            "1. Verify final-medium.md is generated",
            "2. Go to medium.com and click 'Write'",
            "3. Paste formatted content (Medium supports rich paste from Google Docs)",
            "4. Add a subtitle (appears below title in Medium)",
            "5. Set a featured image (Medium crops to 1400x788)",
            "6. Add up to 5 tags",
            "7. Submit to a relevant Medium publication for wider reach",
            "8. Preview on desktop and mobile before publishing",
            "9. Schedule or publish",
        ],
        "seo_tips": [
            "Title: keep under 60 characters; Medium uses it as the page title",
            "Subtitle: 140 characters max; acts as meta description",
            "First 150 characters appear in Google search snippets",
            "Use H2 (##) for section headers \u2014 Medium renders these well",
            "Add alt text to images via Medium's image caption",
            "Include 1-2 links to your other Medium posts for engagement",
            "Publish on Tuesdays or Thursdays for highest engagement",
        ],
        "formatting": [
            "Medium supports Markdown paste but converts to rich text",
            "Use code blocks with ``` \u2014 Medium renders as grey blocks",
            "Medium does not support tables \u2014 use lists or images instead",
            "Embed GitHub gists for longer code (paste gist URL on its own line)",
            "Max 1 image per 300 words for best readability",
        ],
        "limits": {
            "title_max": "100 characters (60 recommended for SEO)",
            "subtitle_max": "140 characters",
            "tags_max": "5 tags",
            "word_range": "800-2500 words (7 min read sweet spot)",
        },
        "tags_advice": "Use popular Medium tags: Programming, JavaScript, Python, Software Development, Technology",
        "checklist": [
            "Title is engaging and < 60 characters",
            "Subtitle is set (< 140 characters)",
            "Featured image is set (1400x788 crop)",
            "5 relevant tags selected",
            "Submitted to a publication",
            "Code blocks render correctly",
            "No tables (converted to lists/images)",
            "Preview checked on mobile",
        ],
    },
    "devto": {
        "name": "dev.to",
        "steps": [
            "1. Verify final-devto.md is generated",
            "2. Go to dev.to/new and paste the content",
            "3. Set the front matter: title, tags, published, cover_image",
            "4. Add canonical_url if cross-posting from your blog",
            "5. Add a cover image (dev.to recommends 1000x420)",
            "6. Select up to 4 tags",
            "7. Preview the article",
            "8. Publish or save as draft",
        ],
        "seo_tips": [
            "dev.to has strong domain authority \u2014 your posts rank well on Google",
            "Include a series header if part of a multi-article series",
            "Use the 'canonical_url' front matter to avoid duplicate content penalties",
            "First 2 sentences appear in search results \u2014 make them count",
            "Tag with popular dev.to tags for discovery: #webdev, #javascript, #tutorial, #beginners",
            "Articles with 'how to' or numbered lists get 2-3x more engagement",
        ],
        "formatting": [
            "Full Markdown support including tables",
            "Front matter block: title, published, tags, cover_image, canonical_url, series",
            "Supports Liquid tags: {% codepen %}, {% github %}, {% youtube %}",
            "Code blocks with language identifier for syntax highlighting",
            "Use {% details Summary %} for collapsible sections",
        ],
        "limits": {
            "title_max": "128 characters",
            "tags_max": "4 tags",
            "cover_image": "1000x420px recommended",
            "word_range": "800-3000 words",
        },
        "tags_advice": "Max 4 tags. Popular: webdev, javascript, python, tutorial, beginners, react, devops",
        "checklist": [
            "Front matter is complete (title, tags, published)",
            "canonical_url set if cross-posting",
            "Cover image uploaded (1000x420px)",
            "4 relevant tags selected",
            "Series field set if part of a series",
            "Liquid tags render correctly",
            "Code blocks have language identifiers",
            "Preview looks good",
        ],
    },
    "hashnode": {
        "name": "Hashnode",
        "steps": [
            "1. Verify final-hashnode.md is generated",
            "2. Go to your Hashnode blog dashboard",
            "3. Click 'Write an article' and paste content",
            "4. Set title, subtitle, and cover image (1600x840)",
            "5. Add tags (up to 5)",
            "6. Configure SEO: custom slug, meta title, meta description",
            "7. Set canonical URL if cross-posting",
            "8. Enable 'Publish to Hashnode Feed' for discovery",
            "9. Preview and publish",
        ],
        "seo_tips": [
            "Hashnode blogs are on your custom domain \u2014 great for personal SEO",
            "Custom slug: use-kebab-case-with-keywords",
            "Meta title can differ from article title \u2014 optimize for search",
            "Enable 'Back up to GitHub' for version control",
            "Articles in Hashnode feed get 5-10x more initial views",
            "Use the series feature for multi-part articles",
        ],
        "formatting": [
            "Full Markdown with extensions",
            "Supports embeds: YouTube, CodePen, CodeSandbox, Twitter",
            "Custom CSS available on paid plans",
            "Cover image: 1600x840px recommended",
            "Table of contents auto-generated from headings",
        ],
        "limits": {
            "title_max": "150 characters",
            "tags_max": "5 tags",
            "cover_image": "1600x840px recommended",
            "word_range": "No strict limit (1000-3000 recommended)",
        },
        "tags_advice": "Use Hashnode's existing tags for discoverability. Popular: JavaScript, Web Development, Python, DevOps",
        "checklist": [
            "Title and subtitle are set",
            "Cover image uploaded (1600x840px)",
            "Up to 5 tags selected",
            "Custom URL slug is SEO-friendly",
            "Meta title and description configured",
            "Canonical URL set if cross-posting",
            "Published to Hashnode Feed enabled",
            "Series configured if applicable",
        ],
    },
    "wechat": {
        "name": "WeChat\u516c\u4f17\u53f7 (WeChat Official Account)",
        "steps": [
            "1. \u786e\u8ba4 final-wechat.md \u5df2\u751f\u6210",
            "2. \u767b\u5f55\u5fae\u4fe1\u516c\u4f17\u5e73\u53f0 (mp.weixin.qq.com)",
            "3. \u70b9\u51fb\u300c\u65b0\u5efa\u56fe\u6587\u300d\uff0c\u7c98\u8d34\u5185\u5bb9",
            "4. \u8bbe\u7f6e\u6807\u9898\u3001\u4f5c\u8005\u3001\u5c01\u9762\u56fe\u7247 (900x383px \u6216 2.35:1)",
            "5. \u6dfb\u52a0\u6458\u8981\uff08\u663e\u793a\u5728\u804a\u5929\u5217\u8868\uff09",
            "6. \u8bbe\u7f6e\u539f\u6587\u94fe\u63a5\uff08\u5982\u6709\u5916\u90e8\u535a\u5ba2\uff09",
            "7. \u9884\u89c8\u5e76\u53d1\u9001\u5230\u624b\u673a\u68c0\u67e5\u6392\u7248",
            "8. \u5b9a\u65f6\u53d1\u5e03\u6216\u7acb\u5373\u53d1\u5e03",
        ],
        "seo_tips": [
            "\u6807\u9898\u63a7\u5236\u572864\u5b57\u4ee5\u5185\uff0c\u524d20\u5b57\u662f\u5173\u952e\u2014\u2014\u641c\u7d22\u7ed3\u679c\u53ea\u663e\u793a\u524d20\u5b57",
            "\u6458\u8981\u5199120\u5b57\u4ee5\u5185\uff0c\u5305\u542b\u6838\u5fc3\u5173\u952e\u8bcd",
            "\u4f7f\u7528\u300c\u641c\u4e00\u641c\u300d\u7684\u70ed\u95e8\u5173\u952e\u8bcd\u505a\u6807\u9898\u4f18\u5316",
            "\u6587\u7ae0\u5f00\u5934\u524d3\u884c\u51b3\u5b9a\u6253\u5f00\u7387\u2014\u2014\u7528\u75db\u70b9/\u95ee\u9898\u5f00\u573a",
            "\u6bcf\u7bc7\u6587\u7ae0\u5e95\u90e8\u52a0\u5f15\u5bfc\u5173\u6ce8\u548c\u5f80\u671f\u63a8\u8350",
            "\u53d1\u5e03\u65f6\u95f4\uff1a\u5de5\u4f5c\u65e5\u665a\u4e0a 8-10\u70b9 \u6216\u5348\u4f11 12-1\u70b9",
            "\u5584\u7528\u8bdd\u9898\u6807\u7b7e (#\u6807\u7b7e#) \u589e\u52a0\u641c\u7d22\u66dd\u5149",
        ],
        "formatting": [
            "\u5fae\u4fe1\u7f16\u8f91\u5668\u4f7f\u7528\u5bcc\u6587\u672c\uff0c\u4e0d\u652f\u6301 Markdown",
            "\u4ee3\u7801\u5757\uff1a\u4f7f\u7528\u5fae\u4fe1\u81ea\u5e26\u4ee3\u7801\u5757\u6216\u622a\u56fe",
            "\u56fe\u7247\u5bbd\u5ea6\u5efa\u8bae 1080px\uff0c\u5c01\u9762 900x383px",
            "\u6bb5\u843d\u95f4\u8ddd\u4fdd\u6301\u4e00\u81f4\uff0c\u4f7f\u7528\u5206\u5272\u7ebf\u5206\u8282",
            "\u6bcf\u5c4f\u4e0d\u8d85\u8fc7 5 \u884c\u6587\u5b57\uff0c\u9002\u914d\u624b\u673a\u9605\u8bfb",
        ],
        "limits": {
            "title_max": "64\u5b57\u7b26",
            "summary_max": "120\u5b57\u7b26",
            "cover_image": "900x383px (2.35:1)",
            "word_range": "1500-4000\u5b57\u4e3a\u4f73",
        },
        "tags_advice": "\u4f7f\u7528\u5fae\u4fe1\u8bdd\u9898\u6807\u7b7e (#\u6807\u7b7e#)\uff0c\u9009\u62e9\u6280\u672f\u70ed\u95e8\u8bdd\u9898",
        "checklist": [
            "\u6807\u9898\u5728 64 \u5b57\u4ee5\u5185\uff0c\u524d 20 \u5b57\u542b\u5173\u952e\u8bcd",
            "\u5c01\u9762\u56fe\u5df2\u8bbe\u7f6e (900x383px)",
            "\u6458\u8981\u5df2\u586b\u5199 (\u2264120\u5b57)",
            "\u4ee3\u7801\u90e8\u5206\u6e32\u67d3\u6b63\u786e",
            "\u624b\u673a\u7aef\u9884\u89c8\u6392\u7248\u6b63\u5e38",
            "\u5f15\u5bfc\u5173\u6ce8\u548c\u5f80\u671f\u63a8\u8350\u5df2\u6dfb\u52a0",
            "\u539f\u6587\u94fe\u63a5\u5df2\u8bbe\u7f6e\uff08\u5982\u9002\u7528\uff09",
        ],
    },
    "juejin": {
        "name": "\u6398\u91d1 (Juejin)",
        "steps": [
            "1. \u786e\u8ba4 final-juejin.md \u5df2\u751f\u6210",
            "2. \u767b\u5f55\u6398\u91d1 (juejin.cn) \u5e76\u70b9\u51fb\u300c\u521b\u4f5c\u8005\u4e2d\u5fc3\u300d",
            "3. \u70b9\u51fb\u300c\u5199\u6587\u7ae0\u300d\uff0c\u7c98\u8d34 Markdown \u5185\u5bb9",
            "4. \u8bbe\u7f6e\u6807\u9898\u3001\u5206\u7c7b\u3001\u6807\u7b7e\uff08\u6700\u591a 3 \u4e2a\uff09",
            "5. \u6dfb\u52a0\u5c01\u9762\u56fe\u7247 (800x450px \u6216 16:9)",
            "6. \u8bbe\u7f6e\u6587\u7ae0\u6458\u8981",
            "7. \u9884\u89c8\u5e76\u53d1\u5e03",
            "8. \u53d1\u5e03\u540e\u5206\u4eab\u5230\u6c89\u91d1/\u5708\u5b50",
        ],
        "seo_tips": [
            "\u6398\u91d1\u6807\u9898\u5728\u641c\u7d22\u5f15\u64ce\u6743\u91cd\u9ad8\u2014\u2014\u4f7f\u7528\u5173\u952e\u8bcd\u5f00\u5934",
            "\u5206\u7c7b\u9009\u62e9\u51c6\u786e\uff1a\u524d\u7aef/\u540e\u7aef/Android/iOS/AI \u7b49",
            "\u6807\u7b7e\u7528\u6280\u672f\u6808\u540d\u79f0\uff1aReact, Vue, Go, Python \u7b49",
            "\u6587\u7ae0\u5f00\u5934\u7528\u7ed3\u8bba\u5148\u884c\uff0c\u518d\u5c55\u5f00\u8bba\u8bc1",
            "\u5584\u7528\u300c\u76f8\u5173\u6587\u7ae0\u300d\u529f\u80fd\u589e\u52a0\u66dd\u5149",
            "\u53d1\u5e03\u65f6\u95f4\uff1a\u5de5\u4f5c\u65e5\u4e0a\u5348 9-11\u70b9 \u6216\u4e0b\u5348 2-4\u70b9",
            "\u6587\u7ae0\u8d28\u91cf\u5206 > 80 \u53ef\u8fdb\u5165\u63a8\u8350\u6c60",
        ],
        "formatting": [
            "\u6398\u91d1\u539f\u751f\u652f\u6301 Markdown",
            "\u4ee3\u7801\u5757\u652f\u6301\u8bed\u6cd5\u9ad8\u4eae\uff08\u6807\u6ce8\u8bed\u8a00\uff09",
            "\u652f\u6301\u8868\u683c\u3001\u4efb\u52a1\u5217\u8868\u3001\u6570\u5b66\u516c\u5f0f",
            "\u5c01\u9762\u56fe\u7247 800x450px (16:9)",
            "\u53ef\u4f7f\u7528\u6398\u91d1 Markdown \u7f16\u8f91\u5668\u5185\u7f6e\u56fe\u5e8a",
        ],
        "limits": {
            "title_max": "80\u5b57\u7b26",
            "tags_max": "3\u4e2a\u6807\u7b7e",
            "cover_image": "800x450px (16:9)",
            "word_range": "1000-5000\u5b57\u4e3a\u4f73",
        },
        "tags_advice": "\u6700\u591a3\u4e2a\u6807\u7b7e\uff0c\u4f7f\u7528\u6280\u672f\u6808\u540d\u79f0\uff08React, Vue, Go, Python\uff09",
        "checklist": [
            "\u6807\u9898\u542b\u5173\u952e\u8bcd\uff0c\u2264 80 \u5b57\u7b26",
            "\u5206\u7c7b\u9009\u62e9\u6b63\u786e",
            "3 \u4e2a\u76f8\u5173\u6807\u7b7e\u5df2\u8bbe\u7f6e",
            "\u5c01\u9762\u56fe\u5df2\u4e0a\u4f20 (800x450px)",
            "\u6458\u8981\u5df2\u586b\u5199",
            "Markdown \u6e32\u67d3\u6b63\u786e",
            "\u4ee3\u7801\u5757\u6807\u6ce8\u4e86\u8bed\u8a00",
            "\u8003\u8651\u53d1\u5e03\u5230\u6c89\u91d1/\u5708\u5b50",
        ],
    },
}


def usage():
    print("""Usage: publishing_guide.py <platform> [project_dir] [--format json]

Platforms: internal external medium devto hashnode wechat juejin all

Options:
  project_dir       Project directory with .essay-state/ for article metadata
  --format json     Output as JSON (default: text)

When project_dir has .essay-state/, reads pipeline-state.json for article title
and seo-metadata.json for tags/keywords/description.""")


def enrich_guide(guide, title, tags, keywords, description):
    """Add article-specific metadata to guide output."""
    meta = {}
    if title:
        meta["article_title"] = title
    if tags:
        tags_max_str = guide["limits"].get("tags_max", "5")
        first_word = tags_max_str.split()[0]
        max_tags = int(first_word) if first_word.isdigit() else 5
        meta["suggested_tags"] = tags[:max_tags]
    if keywords:
        meta["seo_keywords"] = keywords
    if description:
        meta["meta_description"] = description
    return meta


def format_guide_text(name, guide, meta):
    """Format guide as human-readable text."""
    lines = []
    lines.append(f"{'=' * 55}")
    lines.append(f"  Publishing Guide: {name}")
    lines.append(f"{'=' * 55}")
    lines.append("")

    if meta:
        if meta.get("article_title"):
            lines.append(f"  Article: {meta['article_title']}")
        if meta.get("suggested_tags"):
            lines.append(f"  Suggested tags: {', '.join(meta['suggested_tags'])}")
        if meta.get("meta_description"):
            lines.append(f"  Meta description: {meta['meta_description'][:160]}")
        lines.append("")

    lines.append("  Steps:")
    for step in guide["steps"]:
        lines.append(f"    {step}")
    lines.append("")

    lines.append("  SEO Tips:")
    for tip in guide["seo_tips"]:
        lines.append(f"    \u2022 {tip}")
    lines.append("")

    lines.append("  Formatting:")
    for f in guide["formatting"]:
        lines.append(f"    \u2022 {f}")
    lines.append("")

    lines.append("  Limits:")
    for key, val in guide["limits"].items():
        lines.append(f"    {key:20s} {val}")
    lines.append("")

    lines.append(f"  Tags: {guide['tags_advice']}")
    lines.append("")

    lines.append("  Pre-Publish Checklist:")
    for item in guide["checklist"]:
        lines.append(f"    \u25a2 {item}")
    lines.append("")
    lines.append(f"{'=' * 55}")
    return "\n".join(lines)


def format_guide_json(key, guide, meta):
    """Format guide as JSON-serializable dict."""
    result = {
        "platform": key,
        "name": guide["name"],
        "steps": guide["steps"],
        "seo_tips": guide["seo_tips"],
        "formatting": guide["formatting"],
        "limits": guide["limits"],
        "tags_advice": guide["tags_advice"],
        "checklist": guide["checklist"],
    }
    if meta:
        result["article_metadata"] = meta
    return result


def main():
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    platform = sys.argv[1]
    project_dir = ""
    fmt = "text"

    # Parse remaining args
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--format":
            if i + 1 >= len(sys.argv):
                print("ERROR: --format requires a value", file=sys.stderr)
                sys.exit(1)
            fmt = sys.argv[i + 1]
            i += 2
        else:
            project_dir = sys.argv[i]
            i += 1

    # Validate format
    if fmt not in VALID_FORMATS:
        print(f"ERROR: format must be 'text' or 'json'", file=sys.stderr)
        sys.exit(1)

    # Validate platform
    if platform not in VALID_PLATFORMS:
        print(f"ERROR: Invalid platform '{platform}'. Valid: {' '.join(VALID_PLATFORMS)}", file=sys.stderr)
        sys.exit(1)

    # Read article metadata from state if available
    article_title = ""
    article_tags = []
    seo_keywords = []
    article_description = ""

    if project_dir:
        state_dir = os.path.join(project_dir, ".essay-state")
        if os.path.isdir(state_dir):
            # Title from pipeline state
            ps_file = os.path.join(state_dir, "pipeline-state.json")
            ps = read_json_file(ps_file)
            if ps:
                article_title = ps.get("topic", "")

            # Tags and keywords from SEO metadata
            seo_file = os.path.join(state_dir, "seo-metadata.json")
            seo = read_json_file(seo_file)
            if seo:
                article_tags = seo.get("tags", seo.get("keywords", []))
                seo_keywords = seo.get("keywords", [])
                article_description = seo.get("meta_description", seo.get("description", ""))

    # Output
    if platform == "all":
        if fmt == "json":
            results = []
            for key, guide in GUIDES.items():
                meta = enrich_guide(guide, article_title, article_tags, seo_keywords, article_description)
                results.append(format_guide_json(key, guide, meta))
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("\nAvailable platforms:\n")
            for key, guide in GUIDES.items():
                print(f"  \u2022 {key:12s} {guide['name']}")
            print(f"\nRun: publishing-guide.sh <platform> for detailed guide\n")
    else:
        guide = GUIDES[platform]
        meta = enrich_guide(guide, article_title, article_tags, seo_keywords, article_description)
        if fmt == "json":
            print(json.dumps(format_guide_json(platform, guide, meta), indent=2, ensure_ascii=False))
        else:
            print(format_guide_text(guide["name"], guide, meta))


if __name__ == "__main__":
    main()
