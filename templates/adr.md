# Architecture Decision Record (ADR) Article Template

## Target Audience & Expertise Level
- **Primary**: Future engineers (including future-you) who will ask "why did we do it this way?"
- **Secondary**: Current team members who need to understand, challenge, or extend the decision
- **Tertiary**: New hires onboarding into a codebase and trying to understand its shape
- **Expertise**: Intermediate-to-senior (architects, tech leads, senior engineers making or reviewing decisions)
- **Prerequisite knowledge**: Understands the system's architecture and the problem domain; may not know the historical context or the political constraints that shaped the choice

## Recommended Word Count: 1000-2000 words

## Structure
1. **Title** — ADR-NNN: Short, decisive statement of the choice
   - *Purpose*: The title IS the decision — "Use PostgreSQL for event storage" not "Event storage discussion"
   - *Transition*: From the title to the context that demanded a decision
2. **Context** — What prompted this decision (problem, constraint, opportunity)
   - *Purpose*: Set the scene — what was the state of the world when this decision was needed?
   - *Include*: Business drivers, technical constraints, team capabilities, timeline pressure
   - *Transition*: From "why we needed to decide" to "what we decided"
3. **Decision** — What was decided, stated clearly and concisely
   - *Purpose*: One or two sentences that unambiguously state the choice — no hedging, no burying
   - *Format*: "We will [verb] [specific choice] for [specific scope]"
   - *Transition*: From the decision to its current status
4. **Status** — Proposed, accepted, deprecated, or superseded
   - *Purpose*: Tell the reader whether this decision is still active or has been replaced
   - *Include*: Date of status change, link to superseding ADR if applicable
   - *Transition*: From status to consequences
5. **Consequences** — Trade-offs accepted (positive and negative)
   - *Purpose*: Enumerate both the benefits gained AND the costs accepted — honesty here prevents future confusion
   - *Format*: Separate positive and negative consequences into distinct lists
   - *Transition*: From consequences to "what else we considered"
6. **Alternatives considered** — Other options evaluated and why they were rejected
   - *Purpose*: Show that the decision was informed, not arbitrary — explain why each alternative lost
   - *Include*: For each alternative: brief description, where it excels, why it was rejected
   - *Transition*: From alternatives to the decision criteria
7. **Decision criteria** — The factors that drove the final choice
   - *Purpose*: Make the decision-making framework explicit so it can be re-evaluated if context changes
   - *Include*: Criteria with relative weights — which mattered most and why
   - *Transition*: From criteria to revisitation conditions
8. **Revisitation triggers** — When this decision should be re-evaluated
   - *Purpose*: Decisions have shelf lives — state the conditions under which this ADR should be reopened
   - *Include*: Specific thresholds (e.g., "if write volume exceeds 10k/sec"), time-based reviews, or technology shifts

## Example Hooks
- "We chose PostgreSQL over DynamoDB for our event store, despite DynamoDB's superior write throughput. This ADR explains why consistency guarantees outweighed raw performance for our use case."
- "After evaluating five message queue systems over three weeks, we're adopting NATS. This record captures the criteria, trade-offs, and conditions under which we'd revisit."
- "This decision supersedes ADR-017. Our original choice of GraphQL for internal services created more problems than it solved."
- "We are standardizing on gRPC for all inter-service communication, effective Q2 2024. REST endpoints will be maintained but not extended."
- "The team unanimously rejected the microservices migration. This ADR documents why we're doubling down on the modular monolith."

## Tone
- Neutral, analytical, future-reader-oriented
- Write for someone reading this 2 years from now who asks "why?"
- Present facts and reasoning, not advocacy
- Concise — ADRs should be skimmable; every sentence must carry information
- Definitive — use "we will" not "we might" or "we should consider"
- Timestamped — every claim about current state should be dated or versioned

## Code Density: Medium (15-30%)
- Configuration snippets showing the chosen approach
- Interface definitions or API contracts that result from the decision
- Benchmark code or reproduction scripts when performance is a criterion
- Minimal code — just enough to illustrate the decision, not a tutorial

## Target Length: 1000-2000 words

## Anti-Patterns
- **Advocacy disguised as analysis**: An ADR records a decision with reasoning, not argues for it — keep the tone neutral
- **Missing alternatives**: If you only list the chosen option, readers will assume no alternatives were considered
- **Vague consequences**: "This may have performance implications" is useless — quantify or be specific about the risk
- **No expiration signal**: State the conditions under which this decision should be revisited (e.g., "if write volume exceeds 10k/sec")
- **Too long**: ADRs that exceed 2 pages are essays, not records — distill to the essential reasoning
- **Missing decision criteria weights**: List the criteria AND their relative importance; otherwise readers can't evaluate the trade-offs
- **Decision by committee**: "The team agreed" is not a reason — document the actual technical reasoning
- **Coupling multiple decisions**: One ADR, one decision — if you're deciding both the database AND the caching layer, write two ADRs
- **No date or version**: An undated ADR is almost useless — context changes over time and readers need to know when this was written
- **Retrospective justification**: Write the ADR BEFORE or DURING the decision, not after — post-hoc rationalization is unreliable
- **Missing stakeholders**: Note who was involved in the decision and who was consulted — this matters for accountability
- **Burying the decision**: The decision statement should be findable in under 10 seconds of scanning

## Structural Conventions
- Number ADRs sequentially (ADR-001, ADR-002, etc.)
- Keep a lightweight index file linking all ADRs
- Use consistent status labels: Proposed, Accepted, Deprecated, Superseded
- Link related ADRs bidirectionally (if ADR-023 supersedes ADR-017, both should reference each other)
- Store ADRs close to the code they govern (e.g., `docs/adr/` in the repo root)

## Quality Checklist
- [ ] Title states the decision, not the topic
- [ ] Context explains the forces at play, not just the problem
- [ ] Decision is a single, unambiguous statement
- [ ] Status includes a date
- [ ] Consequences list both positive and negative impacts
- [ ] At least two alternatives are documented with rejection reasons
- [ ] Decision criteria include relative weights
- [ ] Revisitation triggers are specific and measurable
- [ ] The entire ADR fits on two printed pages or less

## Reader Promise
"After reading this, you'll understand WHY this decision was made, WHAT was considered, and WHEN to revisit it"
