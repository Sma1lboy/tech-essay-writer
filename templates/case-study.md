# Case Study Article Template

## Target Audience & Expertise Level
- **Primary**: Engineering leads and architects evaluating whether an approach fits their situation
- **Expertise**: Intermediate-to-senior (makes technology decisions, cares about trade-offs and outcomes)
- **Prerequisite knowledge**: Understands the problem domain; looking for real-world validation, not tutorials

## Recommended Word Count: 2000-4000 words

## Structure
1. **Executive Summary** — Company, problem, result (with metrics)
   - *Purpose*: Give decision-makers the TL;DR upfront — they may not read further if this doesn't resonate
   - *Transition*: From "here's the headline result" to "here's the backstory"
2. **Background** — Company context, tech stack, scale
   - *Purpose*: Establish comparability — readers need to know if this situation matches theirs
   - *Transition*: From context to "what went wrong / what we needed"
3. **Challenge** — The specific problem and constraints
   - *Purpose*: Define the problem precisely — vague challenges lead to vague solutions
   - *Transition*: From problem to "what we considered"
4. **Evaluation** — Options considered and decision criteria
   - *Purpose*: Show the decision-making process; this is where readers learn to evaluate for themselves
   - *Transition*: From evaluation to implementation
5. **Implementation** — How it was built, key design decisions
   - *Purpose*: The technical core — share architecture diagrams, code patterns, and integration details
   - *Transition*: From "how we built it" to "what happened"
6. **Results** — Measurable outcomes, before/after
   - *Purpose*: Hard numbers — latency, cost, reliability, developer velocity; make the impact concrete
   - *Transition*: From results to retrospective
7. **Lessons Learned** — What you'd do differently
   - *Purpose*: Honest retrospective that helps readers avoid your mistakes
   - *Transition*: From lessons to applicability
8. **Applicability** — When this approach does and doesn't apply
   - *Purpose*: Help the reader decide if this fits THEIR situation — be specific about boundary conditions

## Example Hooks
- "We migrated 2.3TB of live data from Postgres to DynamoDB with zero downtime. Latency dropped 74%. Here's the full story, including the parts that almost went wrong."
- "After 18 months of running our own Kubernetes cluster, we moved everything to serverless. Our infrastructure costs dropped by 60% — but that's not why we did it."
- "When our monolith hit 500ms response times under load, we had three options. We chose the one our CTO initially rejected."

## Tone
- Professional, data-driven, evidence-based
- Specific numbers and metrics throughout
- Honest about limitations and trade-offs
- Written to help the reader decide, not to sell the solution

## Code Density: Medium (20-35%)

## Target Length: 2000-4000 words

## Anti-Patterns
- **Vendor pitch disguised as case study**: If you only mention benefits, readers will smell the sales angle
- **Missing numbers**: "Performance improved significantly" is useless — give exact percentages, latencies, costs
- **N=1 generalization**: One company's success doesn't mean universal applicability; be explicit about context
- **Hidden constraints**: Not mentioning your team had 5 senior SREs makes the approach seem easier than it is
- **No failure modes**: Every approach has downsides — showing them builds trust
- **Vague "before" state**: The "after" only matters if readers understand the "before" in concrete terms

## Reader Promise
"After reading this, you'll know if this approach works for your situation"
