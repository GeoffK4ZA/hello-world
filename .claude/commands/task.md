---
name: Task Capture
description: Capture, structure, and prioritize a task
argument-hint: <task description>
allowed-tools: Read, Write, Glob
---

# Task Capture

Capture and structure this task: **$ARGUMENTS**

## Process

1. **Parse the Task**
   - What is the actual deliverable?
   - What's the context/why?
   - Any deadline mentioned?
   - Who's involved?

2. **Enrich with Context**
   - Check `/knowledge/projects/` — does this relate to an active project?
   - Check `/knowledge/people/` — is a stakeholder mentioned?

3. **Prioritize**
   - **P0**: Blocking others or has hard deadline today
   - **P1**: Important, due this week
   - **P2**: Should do, flexible timing
   - **P3**: Nice to have, backlog

4. **Structure the Task**

## Output Format

```markdown
## Task Captured

**Task**: [Clear, actionable description]
**Priority**: P0/P1/P2/P3
**Project**: [Related project or "Standalone"]
**Due**: [Date if known, or "TBD"]
**Stakeholder**: [Who cares about this]

### Why This Matters
[Brief context on importance]

### Definition of Done
- [ ] [Specific completion criteria]
- [ ] [Specific completion criteria]

### Next Action
[The very next physical action to move this forward]
```

5. **Save Task**
   - Append to `/knowledge/tasks/active_tasks.md`
   - Or create `/knowledge/tasks/[DATE]_[task-slug].md` for complex tasks

6. **Return Confirmation**
   - Confirm task captured
   - Show where it fits in priority stack
   - Suggest if it should be added to Asana (when available)
