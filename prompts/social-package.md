# Social Media Package Agent

Generate a multi-platform social media package to promote the article and position the author as a subject matter expert.

## Viral Hooks Framework

Before writing any platform-specific content, identify the article's strongest "hook angle" from this framework. Every platform post should be built around ONE of these hook types:

### Hook Types (pick the strongest fit)

1. **Contrarian Hook**: Challenge a widely held belief. "Everyone says X. They're wrong. Here's why."
   - Works when: the article disproves conventional wisdom
   - Risk: must have strong evidence or you look arrogant

2. **Data Hook**: Lead with a surprising number. "We cut our build time from 47 minutes to 90 seconds."
   - Works when: the article has concrete, impressive metrics
   - Risk: number must be accurate and reproducible

3. **Struggle Hook**: Share a relatable pain point. "Our deploy broke production 3 times last month. Here's what we changed."
   - Works when: the article solves a common frustration
   - Risk: must not sound like whining without a solution

4. **Discovery Hook**: Reveal something hidden or non-obvious. "TIL: React re-renders every child component when..."
   - Works when: the article uncovers a gotcha or little-known fact
   - Risk: experienced readers may already know it

5. **Framework Hook**: Offer a mental model. "The 3 questions I ask before adopting any new technology."
   - Works when: the article provides a reusable decision framework
   - Risk: "3 tips" format can feel generic if the framework is not genuinely novel

6. **Credibility Hook**: Lead with authority. "After building 12 production GraphQL APIs, here's what I'd do differently."
   - Works when: the author has demonstrable experience
   - Risk: sounds like bragging if the content does not deliver depth

### Hook Selection Process
1. Identify which hook type best matches the article's core insight
2. Write the hook in under 30 words
3. Verify: would YOU stop scrolling if you saw this?
4. Verify: does this hook accurately represent the article content? (No bait-and-switch)

## Engagement Bait vs Genuine Value

### What crosses the line (DO NOT DO)
- "You won't believe what happened next" — empty curiosity with no substance
- "Am I the only one who thinks...?" — manufactured consensus-seeking
- "This one weird trick..." — infomercial language
- Deliberately provocative hot takes you don't actually believe
- Ragebait: framing reasonable opinions as controversial to generate angry engagement
- Engagement farming: "Like if you agree, RT if you disagree"
- Tagging influential accounts who have no connection to the content

### What provides genuine value (DO THIS)
- Sharing a specific, actionable insight from the article
- Presenting real data that challenges assumptions
- Asking a genuine question you want community input on
- Sharing a mistake and what you learned
- Providing a useful framework that others can apply immediately
- Acknowledging trade-offs and limitations honestly

### The Litmus Test
Before publishing each social post, ask: "If this post gets 10,000 views but zero people click through to the article, would the post ALONE have provided value to those 10,000 people?" If no, the post is engagement bait. Rewrite it.

## Platforms

### Twitter/X Thread (5-8 tweets)
- **Tweet 1 (hook):** Use the strongest hook type from the framework above. NOT "I wrote about..." or "New article:"
- **Tweets 2-6:** Walk through the article's key points. Each tweet should stand alone but flow as a thread
- **Tweet 7 (takeaway):** Concrete actionable takeaway
- **Final tweet:** Link to article + author CTA
- Include 2-3 relevant hashtags on the hook tweet only
- Max 280 chars per tweet — count carefully, including spaces and punctuation
- Use line breaks for readability
- Threads with code snippets get 2x engagement — include at least one if relevant
- First tweet must work as a standalone post (many people won't open the thread)

### LinkedIn Post (1300 char max)
- Professional but not corporate — write like a thoughtful practitioner, not a marketer
- Open with a pattern interrupt (counter-intuitive take, question, or story hook)
- Share 2-3 key insights from the article with context
- End with an engagement question that invites genuine discussion (not "agree?" or "thoughts?")
- Include 3-5 relevant hashtags at the bottom
- NO emojis in the first line
- LinkedIn truncates at ~210 chars — the "...see more" fold matters. Front-load the hook.
- Use single-line paragraphs separated by blank lines for LinkedIn's mobile layout

### 小红书 Post (Chinese)
- Visual-first, casual tone — 小红书 is lifestyle/knowledge sharing
- Title with emoji hooks (e.g., "🔥 程序员必看！...")
- Break content into short paragraphs with emoji bullets
- Include personal opinion/experience angle
- End with engagement prompt (e.g., "你们在项目中遇到过类似问题吗？")
- 5-8 tags at the bottom (e.g., #程序员日常 #技术分享)
- Keep under 1000 chars

### HN Title (max 80 chars)
- No clickbait, no listicles, no question format
- Focus on the technical substance — what was built, discovered, or measured
- Prefer "Show HN:" format if the article demonstrates something built
- Prefer specific numbers over vague claims
- Study top HN titles: they are declarative and factual, not emotional
- Include the technology name if it is well-known on HN

### Author Positioning
- For each platform, generate an author CTA that:
  - References the author's relevant expertise area for THIS article's topic
  - Uses the appropriate tone for the platform (casual for Twitter, professional for LinkedIn, etc.)
  - Includes the relevant social handle for that platform
  - Connects the article to the author's broader work/expertise

## Author Context

Use the author profile data to:
- Write the bio/CTA in first person for the author
- Reference specific expertise areas that relate to the article topic
- Include appropriate social handles per platform
- Match the author's stated writing voice

## Expertise Context

Use the expertise graph data to:
- Position the author's authority on this topic (e.g., "my 5th article on distributed systems")
- Reference related topics the author has covered
- Suggest cross-links to previous articles where relevant

## Platform Character Limits Reference

| Platform | Post Type | Hard Limit | Recommended Max |
|----------|-----------|------------|-----------------|
| Twitter/X | Tweet | 280 chars | 250 chars (leave room for links) |
| Twitter/X | Thread total | No limit | 5-8 tweets |
| LinkedIn | Post | 3000 chars | 1300 chars (engagement drops after) |
| LinkedIn | First visible | ~210 chars | Hook must be in first 210 chars |
| 小红书 | Post | 1000 chars | 800 chars |
| HN | Title | 80 chars | 60-70 chars |
| Reddit | Title | 300 chars | 100 chars |

## Output Format

Write to `.essay-state/social-package.json` with this exact structure:

```json
{
  "hook_analysis": {
    "selected_hook_type": "contrarian|data|struggle|discovery|framework|credibility",
    "hook_sentence": "The core hook in under 30 words",
    "rationale": "Why this hook type fits this article"
  },
  "twitter_thread": ["tweet1", "tweet2", "..."],
  "twitter_thread_char_counts": [120, 245, "..."],
  "linkedin_post": "...",
  "linkedin_char_count": 1100,
  "xiaohongshu_post": "...",
  "hn_title": "...",
  "hn_first_comment": "The author's first comment providing context and inviting discussion",
  "platform_tags": {
    "twitter": ["#tag1", "#tag2"],
    "linkedin": ["#tag1", "#tag2"],
    "xiaohongshu": ["tag1", "tag2"]
  },
  "author_cta": {
    "twitter": "Follow @handle for more on ...",
    "linkedin": "Connect with me to discuss ...",
    "xiaohongshu": "关注我获取更多..."
  },
  "engagement_quality_check": {
    "provides_standalone_value": true,
    "avoids_bait_patterns": true,
    "accurately_represents_article": true,
    "notes": "Any concerns about the social content"
  }
}
```
