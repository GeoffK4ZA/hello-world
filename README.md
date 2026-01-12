# Geoff OS

> Autonomous AI Operating System — Your Digital Chief of Staff

An intelligent assistant built on Claude Code that operates as an extension of you. Not a chatbot — a second version of yourself running in the background.

## What It Does

| Capability | How |
|------------|-----|
| **Daily Operations** | `/brief` generates priority stacks, calendar overview, focus areas |
| **Meeting Prep** | `/prep` creates comprehensive preparation packs |
| **Task Management** | `/task` captures, prioritizes, and tracks work |
| **Project Awareness** | `/status` provides health checks and analysis |
| **Drafting** | `/draft` writes emails, messages, docs in your voice |
| **Proposals** | Auto-triggered skill for scoping and quoting |

## Architecture

```
geoff-os/
├── CLAUDE.md                    # Identity, voice, rules
├── .claude/
│   ├── commands/                # User-triggered commands
│   │   ├── brief.md             # /brief
│   │   ├── prep.md              # /prep <meeting>
│   │   ├── task.md              # /task <description>
│   │   ├── status.md            # /status <project>
│   │   └── draft.md             # /draft <type>
│   ├── skills/                  # Auto-triggered expertise
│   │   ├── knowledge-retriever/ # Context retrieval
│   │   ├── project-analyst/     # Project health analysis
│   │   ├── proposal-writer/     # Proposal generation
│   │   └── meeting-prep/        # Meeting preparation
│   └── agents/                  # Parallel subagents
│       ├── researcher/          # Deep research
│       ├── drafter/             # Writing specialist
│       └── analyst/             # Analysis specialist
├── knowledge/                   # Your context (RAG source)
│   ├── projects/                # Active project files
│   ├── people/                  # Stakeholder profiles
│   ├── clients/                 # Client information
│   ├── decisions/               # Decision records
│   ├── templates/               # Reusable templates
│   └── tasks/                   # Task tracking
├── artefacts/                   # Generated outputs
│   ├── briefs/
│   ├── meeting-prep/
│   ├── proposals/
│   ├── drafts/
│   └── status-reports/
└── jobs/                        # Job audit logs
```

## How It Works

1. **Commands** (`/brief`, `/prep`, etc.) — You trigger explicitly
2. **Skills** — Auto-activate based on what you're discussing
3. **Subagents** — Run in parallel for complex multi-part requests
4. **Knowledge Base** — Grounds all outputs in your actual context
5. **Artefacts** — Every meaningful output is saved

## Quick Start

### 1. Add Your Context

Create project files in `/knowledge/projects/`:
```bash
cp knowledge/templates/project-template.md knowledge/projects/my-project.md
# Edit with your project details
```

Add key people to `/knowledge/people/`:
```bash
cp knowledge/templates/person-template.md knowledge/people/sarah-chen.md
# Edit with stakeholder details
```

### 2. Use Commands

```
/brief                    # Get your daily operating brief
/prep Q1 Planning         # Prepare for Q1 Planning meeting
/task Review the proposal # Capture a new task
/status all               # Get portfolio status
/draft email to Sarah     # Draft an email
```

### 3. Let Skills Help

Just describe what you need — skills activate automatically:
- "Help me write a proposal for Acme Corp" → `proposal-writer` activates
- "What's the status of Project Alpha?" → `project-analyst` activates
- "Prepare me for my meeting with Sarah" → `meeting-prep` activates

## Design Principles

1. **Execution over explanation** — Do the work, don't describe it
2. **Context is everything** — Always retrieve before acting
3. **Artefacts are proof** — Save every meaningful output
4. **Anticipate, don't wait** — Surface issues proactively
5. **Quality bar** — Everything should feel consultant-grade

## Requirements

- Claude Code CLI
- Claude Max subscription (for $0 operation)

## Extending

### Add a New Command

Create `.claude/commands/my-command.md`:
```markdown
---
name: My Command
description: What it does
allowed-tools: Read, Write, Glob
---

# My Command

Instructions for Claude...
```

### Add a New Skill

Create `.claude/skills/my-skill/SKILL.md`:
```markdown
---
name: my-skill
description: Triggers when [conditions] for [purpose]
tags: keyword1, keyword2
allowed-tools: Read, Glob, Grep
---

# My Skill

When to activate and what to do...
```

## The Vision

Geoff OS isn't just an assistant — it's a second you. It knows your projects, your people, your preferences. It anticipates what you need. It makes you look amazing.

---

*Built with Claude Code*
