# Deep Dive Article Template

## Target Audience & Expertise Level
- **Primary**: Mid-to-senior engineers who use the technology and want to understand it deeply
- **Expertise**: Intermediate-to-advanced (has practical experience, wants the "why" behind the "how")
- **Prerequisite knowledge**: Working familiarity with the domain; has opinions but wants sharper ones

## Recommended Word Count: 2500-5000 words

## Structure
1. **Hook** — The surprising insight or question
   - *Purpose*: Challenge a common assumption or reveal something non-obvious
   - *Transition*: From "here's what most people get wrong" to "here's the context"
2. **Context** — Why this matters now
   - *Purpose*: Ground the deep dive in a current shift, incident, or trend that makes it timely
   - *Transition*: From "why now" to "what makes this hard"
3. **Problem Space** — What makes this hard
   - *Purpose*: Map the complexity landscape — show the constraints, tensions, and trade-off surfaces
   - *Transition*: From "here's the challenge" to "let me show you the internals"
4. **Analysis** — Deep technical exploration with diagrams
   - *Purpose*: The meat of the article — walk through the internals, algorithms, or architecture
   - *Transition*: From detailed analysis to "how to think about it"
5. **Architecture / Design** — How to think about it
   - *Purpose*: Elevate from specifics to mental models and design principles
   - *Transition*: From mental models to practical trade-offs
6. **Trade-offs** — What you gain and lose
   - *Purpose*: Honest assessment of costs, not just benefits — this builds trust
   - *Transition*: From trade-offs to "so what should I do?"
7. **Recommendations** — Opinionated guidance
   - *Purpose*: Give concrete, actionable advice based on the analysis — don't leave readers hanging
   - *Transition*: From recommendations to the big-picture takeaway
8. **Conclusion** — The takeaway that changes how you think
   - *Purpose*: Crystallize the single most important insight into a memorable statement

## Example Hooks
- "Everyone says X is fast. The benchmarks prove it. But when we deployed it at scale, we discovered the benchmarks were measuring the wrong thing entirely."
- "The official documentation explains WHAT the garbage collector does. It never explains WHY it makes the choices it does. That 'why' cost us a week of debugging."
- "There are 14 blog posts explaining how to configure X. None of them explain the one setting that actually matters."

## Tone
- Authoritative, analytical, "here's what I've learned"
- First person when sharing experience
- Balance theory with practical examples
- Respectful of the reader's time — every paragraph earns its place

## Code Density: Medium (20-30%)

## Target Length: 2500-5000 words

## Anti-Patterns
- **Surface-level analysis**: If you're restating the docs, you're not deep-diving; add original insight
- **No diagrams**: Deep dives almost always need at least one visual — architecture, flow, or comparison
- **Missing benchmarks**: Claims about performance without numbers are opinions, not analysis
- **Jargon without grounding**: Define terms on first use or link to explanations — even for expert readers
- **"It depends" without guidance**: Acknowledging complexity is good; failing to give an opinion is not
- **Scope creep**: Pick one thing and go deep rather than covering three things at surface level

## Reader Promise
"After reading this, you'll understand WHY X works the way it does"
