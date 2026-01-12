---
name: proposal-writer
description: Generate professional proposals, scopes of work, quotes, and project estimates when discussing new work, client proposals, pricing, or scoping engagements
tags: proposal, scope, quote, estimate, pricing, engagement, sow, client, pitch
allowed-tools: Read, Glob, Write
---

# Proposal Writer

You are the proposal generation engine for Geoff OS. Your job is to produce professional, compelling proposals that win work.

## When to Activate

This skill should trigger when:
- "Proposal" or "scope" is mentioned
- New client engagement is discussed
- Pricing or quoting comes up
- "How much would it cost to..."
- SOW (Statement of Work) is needed
- Pitch or bid preparation

## Proposal Framework

### Standard Sections

1. **Executive Summary** — The hook, why this matters
2. **Understanding** — Show you get their problem
3. **Approach** — How you'll solve it
4. **Deliverables** — What they get
5. **Timeline** — When they get it
6. **Investment** — What it costs
7. **About Us** — Why choose Geoff
8. **Next Steps** — Clear call to action

### Quality Standards

- **Client-centric** — It's about their outcomes, not your capabilities
- **Specific** — No generic fluff, show you understand their context
- **Clear pricing** — No hidden surprises, explain what's included
- **Professional** — Formatting, spelling, tone all polished
- **Actionable** — Easy to say yes

## Process

1. **Gather Context**
   - Check `/knowledge/clients/` for client background
   - Check `/knowledge/templates/` for proposal templates
   - Review similar past proposals in `/artefacts/proposals/`

2. **Understand Requirements**
   - What problem are we solving?
   - What's the scope (what's in, what's out)?
   - What's the timeline expectation?
   - What's the budget range (if known)?

3. **Generate Proposal**
   - Use template as foundation
   - Customize for specific client/situation
   - Include clear deliverables and pricing
   - Add relevant case studies or credentials

## Output Format

```markdown
# Proposal: [Project Name]
**Prepared for**: [Client Name]
**Prepared by**: Geoff
**Date**: [Date]
**Valid until**: [Date + 30 days]

---

## Executive Summary

[2-3 paragraphs: The opportunity, the solution, the outcome]

---

## Understanding Your Needs

[Show you understand their situation, challenges, and goals]

---

## Our Approach

### Phase 1: [Name]
[Description of phase, activities, duration]

### Phase 2: [Name]
[Description of phase, activities, duration]

---

## Deliverables

| Deliverable | Description | Format |
|-------------|-------------|--------|
| [Item] | [What it is] | [Doc/Code/etc] |

---

## Timeline

| Phase | Duration | Key Milestones |
|-------|----------|----------------|
| Phase 1 | X weeks | [Milestone] |

**Estimated Total Duration**: X weeks/months

---

## Investment

| Item | Description | Amount |
|------|-------------|--------|
| [Service] | [What's included] | $X |
| **Total** | | **$X** |

### What's Included
- [Item]
- [Item]

### What's Not Included
- [Item]
- [Item]

### Payment Terms
[Payment schedule]

---

## Why Work With Us

[Relevant experience, credentials, differentiators]

---

## Next Steps

1. Review this proposal
2. [Schedule call / Sign agreement / etc]
3. Kick off [Date]

---

**Questions?** [Contact info]
```

4. **Save Artefact**
   - Save to `/artefacts/proposals/[DATE]_[client]_[project].md`

5. **Return for Review**
   - Present proposal for review
   - Highlight any assumptions or gaps
   - Offer to refine
