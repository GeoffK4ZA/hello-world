---
name: Daily Brief
description: Generate daily plan with priorities, calendar overview, and focus areas
allowed-tools: Read, Glob, Grep, Write
---

# Daily Brief

Generate Geoff's daily operating brief.

## Process

1. **Retrieve Context**
   - Read `/knowledge/projects/` for active projects and their status
   - Check for any calendar context in `/knowledge/calendar/`
   - Review recent artefacts in `/artefacts/` for continuity

2. **Analyze**
   - What's most urgent today?
   - What meetings need prep?
   - What deadlines are approaching?
   - What's been stuck and needs attention?

3. **Generate Brief**

## Output Format

```markdown
# Daily Brief — [DATE]

## Today's Priority Stack
1. **[P0]** [Most critical item]
2. **[P1]** [Second priority]
3. **[P2]** [Third priority]

## Calendar Overview
| Time | Meeting | Prep Status |
|------|---------|-------------|
| HH:MM | Meeting name | Ready / Needs prep |

## Project Pulse
| Project | Status | Next Action |
|---------|--------|-------------|
| Name | 🟢/🟡/🔴 | What's next |

## Blockers & Risks
- [Any blockers that need escalation]

## Focus Areas
- [What to protect time for today]

## End of Day Target
- [What does "good" look like by EOD?]
```

4. **Save Artefact**
   - Save to `/artefacts/briefs/[DATE]_daily_brief.md`

5. **Return Summary**
   - Return the brief directly
   - Highlight any items needing immediate attention
