---
name: Meeting Prep
description: Generate meeting preparation pack with agenda, talking points, and stakeholder context
argument-hint: <meeting name or topic>
allowed-tools: Read, Glob, Grep, Write
---

# Meeting Prep

Generate a comprehensive meeting preparation pack for: **$ARGUMENTS**

## Process

1. **Gather Context**
   - Search `/knowledge/projects/` for related project context
   - Search `/knowledge/people/` for attendee profiles
   - Check `/knowledge/decisions/` for relevant past decisions
   - Review any previous meeting notes in `/artefacts/meeting-prep/`

2. **Analyze**
   - What's the meeting objective?
   - Who are the key stakeholders and what do they care about?
   - What decisions need to be made?
   - What questions might come up?

3. **Generate Prep Pack**

## Output Format

```markdown
# Meeting Prep: [MEETING NAME]
**Date**: [If known]
**Duration**: [If known]

## Objective
[What success looks like for this meeting]

## Attendees
| Name | Role | What They Care About |
|------|------|---------------------|
| Name | Title | Key interests/concerns |

## Agenda
1. [Topic] — [Time allocation]
2. [Topic] — [Time allocation]
3. [Topic] — [Time allocation]

## Talking Points
- **Open with**: [How to start]
- **Key message**: [Main point to land]
- **Evidence**: [Data or examples to reference]

## Anticipated Questions
| Question | Suggested Response |
|----------|-------------------|
| [Question] | [Response approach] |

## Decisions Needed
- [ ] [Decision 1]
- [ ] [Decision 2]

## Context & Background
[Relevant history, previous discussions, current status]

## Pre-Meeting Actions
- [ ] [Any prep needed before the meeting]

## Post-Meeting Template
- Decisions made:
- Action items:
- Follow-ups needed:
```

4. **Save Artefact**
   - Save to `/artefacts/meeting-prep/[DATE]_[meeting-slug].md`

5. **Return Prep Pack**
   - Return the full prep pack
   - Highlight any missing context that should be gathered
