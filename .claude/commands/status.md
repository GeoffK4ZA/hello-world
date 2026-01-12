---
name: Project Status
description: Get comprehensive status on a specific project or all projects
argument-hint: <project name or "all">
allowed-tools: Read, Glob, Grep, Write
---

# Project Status

Generate status report for: **$ARGUMENTS**

## Process

1. **Identify Scope**
   - If specific project: focus on that project
   - If "all" or empty: summarize all active projects

2. **Gather Information**
   - Read project file from `/knowledge/projects/`
   - Check recent artefacts related to the project
   - Look for any blockers or risks noted

3. **Analyze**
   - Overall health: 🟢 On Track / 🟡 At Risk / 🔴 Blocked
   - Progress against milestones
   - Open issues and blockers
   - Upcoming deadlines

4. **Generate Status**

## Output Format (Single Project)

```markdown
# Project Status: [PROJECT NAME]
**Generated**: [DATE]
**Health**: 🟢/🟡/🔴

## Summary
[2-3 sentence executive summary]

## Progress
| Milestone | Status | Due | Notes |
|-----------|--------|-----|-------|
| Milestone 1 | ✅/🔄/⏳ | Date | Notes |

## Current Sprint/Focus
- [What's actively being worked on]

## Blockers
| Blocker | Owner | Impact | Action |
|---------|-------|--------|--------|
| Issue | Who | H/M/L | Next step |

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Risk | H/M/L | H/M/L | Plan |

## Key Stakeholders
| Name | Role | Last Touchpoint |
|------|------|-----------------|
| Name | Role | When |

## Next Actions
1. [Action] — [Owner] — [Due]
2. [Action] — [Owner] — [Due]

## Decisions Pending
- [ ] [Decision needed]
```

## Output Format (All Projects)

```markdown
# Portfolio Status
**Generated**: [DATE]

## Health Overview
| Project | Health | Next Milestone | Blockers |
|---------|--------|----------------|----------|
| Project 1 | 🟢/🟡/🔴 | What's next | Count |

## Attention Required
[Projects that need immediate focus]

## This Week's Priorities
1. [Priority across portfolio]
2. [Priority across portfolio]

## Resource Conflicts
[Any competing priorities or resource issues]
```

5. **Save Artefact**
   - Save to `/artefacts/status-reports/[DATE]_[project-or-portfolio].md`

6. **Return Status**
   - Return full status report
   - Highlight anything needing immediate attention
