# Social Media Package Agent

Generate a multi-platform social media package to promote the article and position the author as a subject matter expert.

## Platforms

### Twitter/X Thread (5-8 tweets)
- **Tweet 1 (hook):** Start with a surprising insight, bold claim, or relatable frustration — NOT "I wrote about..." or "New article:"
- **Tweets 2-6:** Walk through the article's key points. Each tweet should stand alone but flow as a thread
- **Tweet 7 (takeaway):** Concrete actionable takeaway
- **Final tweet:** Link to article + author CTA
- Include 2-3 relevant hashtags on the hook tweet only
- Max 280 chars per tweet
- Use line breaks for readability

### LinkedIn Post (1300 char max)
- Professional but not corporate — write like a thoughtful practitioner, not a marketer
- Open with a pattern interrupt (counter-intuitive take, question, or story hook)
- Share 2-3 key insights from the article with context
- End with an engagement question that invites genuine discussion (not "agree?")
- Include 3-5 relevant hashtags at the bottom
- NO emojis in the first line

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

## Output Format

Write to `.essay-state/social-package.json` with this exact structure:

```json
{
  "twitter_thread": ["tweet1", "tweet2", "..."],
  "linkedin_post": "...",
  "xiaohongshu_post": "...",
  "hn_title": "...",
  "platform_tags": {
    "twitter": ["#tag1", "#tag2"],
    "linkedin": ["#tag1", "#tag2"],
    "xiaohongshu": ["tag1", "tag2"]
  },
  "author_cta": {
    "twitter": "Follow @handle for more on ...",
    "linkedin": "Connect with me to discuss ...",
    "xiaohongshu": "关注我获取更多..."
  }
}
```
