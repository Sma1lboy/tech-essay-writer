# Release Announcement Article Template

## Target Audience & Expertise Level
- **Primary**: Existing users who need to decide whether and how to upgrade
- **Secondary**: Potential users evaluating the project for the first time
- **Expertise**: Mixed — from beginners checking compatibility to power users scanning for breaking changes
- **Prerequisite knowledge**: Basic familiarity with the product; upgraders need to know their current version

## Recommended Word Count: 1000-2500 words

## Structure
1. **Headline feature** — The one thing that makes this release worth upgrading for
   - *Purpose*: Lead with the single most compelling change — don't dilute with a feature list
   - *Transition*: From the headline to the full changelog
2. **What's new** — Categorized changes (features, improvements, fixes)
   - *Purpose*: Comprehensive but scannable — group by category, lead each item with user impact
   - *Transition*: From "what changed" to "how to upgrade"
3. **Migration guide** — Step-by-step upgrade path with code examples
   - *Purpose*: Make upgrading feel safe and achievable — show before/after code for every breaking change
   - *Transition*: From migration steps to explicit breakage list
4. **Breaking changes** — What will break and how to fix it
   - *Purpose*: Earn trust through transparency — users hate discovering breaking changes after upgrading
   - *Transition*: From what broke to what's coming
5. **What's next** — Roadmap tease and upcoming priorities
   - *Purpose*: Build excitement for the trajectory; show the release is part of a larger vision
   - *Transition*: From roadmap to immediate action
6. **Try it now** — Clear CTA with install/upgrade commands
   - *Purpose*: Remove all friction — copy-paste commands that work immediately

## Example Hooks
- "v3.0 brings native streaming support — the feature you've requested 847 times on GitHub. Here's everything that's new and how to upgrade in under 5 minutes."
- "This release cuts cold-start time by 62%. If you've been waiting for a reason to upgrade, this is it."
- "Two years in the making: v2.0 is a complete rewrite of the rendering engine. Same API, 3x the performance."

## Tone
- Excited but precise, "here's what we shipped and why it matters"
- Lead with user impact, not implementation details
- Make upgrade feel easy and worthwhile
- Grateful to community — acknowledge contributors and feedback that shaped the release

## Code Density: High (30-40%)

## Target Length: 1000-2500 words

## Anti-Patterns
- **Feature dump without priorities**: Not every change is equally important — lead with the headliner, not a flat list
- **Missing migration guide**: Announcing breaking changes without showing the fix is just delivering bad news
- **Internal jargon**: "Refactored the AST walker" means nothing to users — translate to impact: "faster parsing"
- **No install/upgrade command**: The CTA must be a copy-paste command, not "check the docs"
- **Burying breaking changes**: Put them in a clearly labeled section; hiding them erodes trust
- **No version pinning advice**: Tell users which version to pin if they can't upgrade immediately

## Reader Promise
"After reading this, you'll know what changed and how to upgrade"
