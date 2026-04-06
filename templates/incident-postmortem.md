# Incident Post-Mortem Article Template

## Target Audience & Expertise Level
- **Primary**: SREs, platform engineers, and engineering leads who want to prevent similar failures
- **Expertise**: Intermediate-to-senior (understands distributed systems, monitoring, and incident response)
- **Prerequisite knowledge**: Familiar with infrastructure concepts; comfortable reading logs and metrics

## Recommended Word Count: 1500-3000 words

## Structure
1. **TL;DR** — What happened, impact scope, resolution time
   - *Purpose*: Give the executive summary upfront — severity, duration, blast radius, resolution
   - *Transition*: From summary to detailed chronology
2. **Timeline** — Chronological events (detection -> investigation -> mitigation -> resolution)
   - *Purpose*: Precise chronology with timestamps — this is the forensic backbone of the post-mortem
   - *Transition*: From "what happened when" to "why it happened"
3. **Root cause analysis** — The actual underlying cause, not just the trigger
   - *Purpose*: Go beyond the proximate cause to the systemic failure — "why did the guard rails not catch this?"
   - *Transition*: From root cause to response narrative
4. **What we tried** — Approaches attempted during the incident, including dead ends
   - *Purpose*: Show the investigation process honestly — dead ends are as instructive as the fix
   - *Transition*: From attempts to the resolution
5. **What worked** — The fix and why it worked
   - *Purpose*: Explain the specific remediation and why it addressed the root cause, not just the symptom
   - *Transition*: From fix to forward-looking prevention
6. **Action items** — Concrete follow-ups with owners and timelines
   - *Purpose*: Convert lessons into tracked commitments — vague "we should" statements don't count
   - *Transition*: From action items to broader lessons
7. **Lessons learned** — Systemic takeaways beyond this specific incident
   - *Purpose*: Extract the generalizable principle — what class of failure does this represent?

## Example Hooks
- "On March 15 at 03:22 UTC, 100% of API requests to our payment service began returning 503s. The outage lasted 47 minutes and affected 2.3M transactions. The root cause was a 4-byte configuration change deployed 6 days earlier."
- "Our monitoring told us everything was fine. Our users told us everything was broken. This is the story of the 90-minute gap between reality and our dashboards."
- "The incident started with a routine deploy. It ended with us rewriting our entire rollback strategy."

## Tone
- Honest, blameless, data-driven
- Focus on systems and processes, not individuals
- Specific timestamps, metrics, and error messages
- Clinical precision combined with narrative clarity

## Code Density: Low-Medium (10-25%)

## Target Length: 1500-3000 words

## Anti-Patterns
- **Blame assignment**: Name systems, not people; "the deploy pipeline lacked rollback guards" not "John deployed without testing"
- **Missing timestamps**: A timeline without precise timestamps is just a story — include UTC times for every event
- **Root cause = trigger**: "The server crashed because of high load" is the trigger; the root cause is why the system couldn't handle that load
- **Vague action items**: "Improve monitoring" is not an action item; "Add latency P99 alert threshold at 500ms to payment-service by March 30 (owner: SRE team)" is
- **Premature lessons**: Don't claim systemic lessons before the investigation is complete — premature conclusions lead to wrong fixes
- **Sanitized narrative**: Hiding the dead ends makes the post-mortem less useful — show what you tried and why it didn't work

## Reader Promise
"After reading this, you'll know how to prevent this class of failure"
