#!/usr/bin/env python3
"""SEO metadata generator — produces OpenGraph, meta tags, JSON-LD, keyword density.
Usage: seo_metadata.py <project_dir> [verbose]
"""

import json
import os
import re
import sys
from collections import Counter

from utils import atomic_json_write, read_json_file


def usage():
    print("""Usage: seo_metadata.py <project_dir> [verbose]

Generates SEO metadata including OpenGraph tags, meta tags, Twitter card,
JSON-LD structured data, and keyword density analysis.

Reads: final-external.md or latest draft, review-seo.json, pipeline-state.json
Writes: seo-metadata.json

Output: JSON result to stdout (or verbose text with 'verbose' flag)""")


def main():
    project_dir = sys.argv[1] if len(sys.argv) > 1 else ""
    verbose = len(sys.argv) > 2 and sys.argv[2] == "verbose"

    if not project_dir:
        print("ERROR: project_dir required", file=sys.stderr)
        print("Usage: seo_metadata.py <project_dir> [verbose]", file=sys.stderr)
        sys.exit(1)

    state_dir = os.path.join(project_dir, ".essay-state")

    # --- Read inputs directly from state files ---

    # Find best article: final-external > latest draft
    article_content = ""
    article_source = ""
    final_ext = os.path.join(state_dir, "final-external.md")
    if os.path.exists(final_ext):
        with open(final_ext) as f:
            article_content = f.read()
        article_source = "final-external.md"
    else:
        for i in range(10, 0, -1):
            draft = os.path.join(state_dir, f"draft-v{i}.md")
            if os.path.exists(draft):
                with open(draft) as f:
                    article_content = f.read()
                article_source = f"draft-v{i}.md"
                break

    # Read SEO review
    seo_file = os.path.join(state_dir, "review-seo.json")
    seo_review = read_json_file(seo_file)

    # Read pipeline state
    ps_file = os.path.join(state_dir, "pipeline-state.json")
    pipeline_state = read_json_file(ps_file)

    # --- Extract article metadata ---
    topic = pipeline_state.get("topic", "")
    language = pipeline_state.get("language", "en")

    # Extract title from first heading
    title = topic  # fallback
    lines = article_content.split("\n") if article_content else []
    for line in lines:
        line_s = line.strip()
        if line_s.startswith("# ") and not line_s.startswith("## "):
            title = line_s[2:].strip()
            break

    # Extract first paragraph as description candidate
    description = ""
    in_content = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            in_content = True
            continue
        if in_content and stripped and not stripped.startswith("#") and not stripped.startswith("```"):
            description = stripped[:160]
            break

    if not description:
        description = f"A technical article about {topic}" if topic else "A technical article"

    # Get author from pipeline state or default
    author = pipeline_state.get("author", "")

    # --- Keywords from SEO review + article analysis ---
    seo_keywords = seo_review.get("keywords", seo_review.get("target_keywords", []))
    if isinstance(seo_keywords, str):
        seo_keywords = [k.strip() for k in seo_keywords.split(",")]

    # --- Keyword Density Analysis ---
    # Clean article text: remove code blocks, markdown syntax, URLs
    clean_text = article_content
    clean_text = re.sub(r'```[\s\S]*?```', '', clean_text)
    clean_text = re.sub(r'`[^`]+`', '', clean_text)
    clean_text = re.sub(r'https?://\S+', '', clean_text)
    clean_text = re.sub(r'[#*_\[\]()>|]', ' ', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    words = clean_text.lower().split()
    total_words = len(words)

    # Stop words to exclude
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "it", "its",
        "this", "that", "these", "those", "i", "you", "he", "she", "we",
        "they", "my", "your", "his", "her", "our", "their", "not", "no",
        "if", "then", "else", "when", "where", "how", "what", "which",
        "who", "whom", "why", "all", "each", "every", "both", "few",
        "more", "most", "other", "some", "such", "than", "too", "very",
        "just", "about", "above", "after", "before", "between", "into",
        "through", "during", "out", "up", "down", "over", "under", "so",
        "as", "also", "like", "use", "using", "used", "one", "two"
    }

    filtered = [w for w in words if len(w) > 2 and w not in stop_words and w.isalpha()]
    word_freq = Counter(filtered)

    # Top keywords by frequency
    keyword_density = []
    for word, count in word_freq.most_common(15):
        density = round((count / total_words) * 100, 2) if total_words > 0 else 0
        keyword_density.append({
            "keyword": word,
            "count": count,
            "density_percent": density
        })

    # Combine SEO-recommended keywords with density data
    all_keywords = list(seo_keywords) if isinstance(seo_keywords, list) else []
    for kd in keyword_density[:5]:
        if kd["keyword"] not in [k.lower() for k in all_keywords]:
            all_keywords.append(kd["keyword"])
    all_keywords = all_keywords[:10]

    # --- Build SEO metadata ---

    # OpenGraph tags
    opengraph_tags = {
        "og:title": title,
        "og:description": description[:200],
        "og:type": "article",
        "og:image": "{{OG_IMAGE_URL}}",
        "og:url": "{{CANONICAL_URL}}",
        "og:site_name": "{{SITE_NAME}}",
        "og:locale": "zh_CN" if language == "zh" else "en_US",
        "article:published_time": "{{PUBLISH_DATE}}",
        "article:author": author if author else "{{AUTHOR_URL}}",
        "article:tag": all_keywords[:5]
    }

    # Meta tags
    meta_tags = {
        "description": description[:160],
        "keywords": ", ".join(all_keywords),
        "author": author if author else "{{AUTHOR_NAME}}",
        "robots": "index, follow",
        "viewport": "width=device-width, initial-scale=1.0"
    }

    # Canonical URL
    canonical_url = "{{CANONICAL_URL}}"

    # Twitter card
    twitter_card = {
        "twitter:card": "summary_large_image",
        "twitter:title": title[:70],
        "twitter:description": description[:200],
        "twitter:image": "{{OG_IMAGE_URL}}",
        "twitter:site": "{{TWITTER_HANDLE}}",
        "twitter:creator": "{{TWITTER_HANDLE}}"
    }

    # JSON-LD structured data (Article schema)
    structured_data = {
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": title[:110],
        "description": description[:200],
        "author": {
            "@type": "Person",
            "name": author if author else "{{AUTHOR_NAME}}",
            "url": "{{AUTHOR_URL}}"
        },
        "publisher": {
            "@type": "Organization",
            "name": "{{PUBLISHER_NAME}}",
            "logo": {
                "@type": "ImageObject",
                "url": "{{PUBLISHER_LOGO_URL}}"
            }
        },
        "datePublished": "{{PUBLISH_DATE}}",
        "dateModified": "{{MODIFY_DATE}}",
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": "{{CANONICAL_URL}}"
        },
        "image": "{{OG_IMAGE_URL}}",
        "keywords": all_keywords,
        "wordCount": total_words,
        "inLanguage": "zh-CN" if language == "zh" else "en-US",
        "articleSection": topic if topic else "Technology"
    }

    result = {
        "opengraph_tags": opengraph_tags,
        "meta_tags": meta_tags,
        "canonical_url": canonical_url,
        "twitter_card": twitter_card,
        "structured_data": structured_data,
        "keyword_density": keyword_density,
        "total_words": total_words,
        "title": title,
        "description": description
    }

    if verbose:
        print(f"\n{'='*40}")
        print(f"SEO Metadata for: {title}")
        print(f"Description: {description[:80]}...")
        print(f"Keywords: {', '.join(all_keywords[:5])}")
        print(f"Word count: {total_words}")
        print(f"\nTop keywords by density:")
        for kd in keyword_density[:10]:
            bar = "\u2588" * max(1, int(kd["density_percent"] * 10))
            print(f"  {kd['keyword']:20s} {bar} {kd['density_percent']}% ({kd['count']}x)")
        print(f"\nJSON-LD type: {structured_data['@type']}")
        print(f"OG type: {opengraph_tags['og:type']}")
        print(f"Twitter card: {twitter_card['twitter:card']}")
    else:
        print(json.dumps(result))

    # Atomic write to state
    target_file = os.path.join(state_dir, "seo-metadata.json")
    atomic_json_write(target_file, result)


if __name__ == "__main__":
    main()
