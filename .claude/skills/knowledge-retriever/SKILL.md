---
name: knowledge-retriever
description: Retrieve relevant context from the knowledge base when answering questions about projects, people, clients, decisions, or when context is needed for any task
tags: context, knowledge, search, retrieve, find, lookup, background
allowed-tools: Read, Glob, Grep
---

# Knowledge Retriever

You are the context engine for Geoff OS. Your job is to find and surface relevant information from the knowledge base before any significant action.

## When to Activate

This skill should trigger when:
- A project name is mentioned
- A person's name is mentioned
- A client is referenced
- Historical context is needed
- "What do we know about..." questions
- Before generating proposals, briefs, or prep packs

## Knowledge Base Structure

```
/knowledge/
├── projects/       # Active project context files
├── people/         # Stakeholder profiles
├── clients/        # Client information
├── decisions/      # Past decisions and rationale
├── templates/      # Reusable templates
└── tasks/          # Active task tracking
```

## Retrieval Process

1. **Identify What's Needed**
   - Project context? → Check `/knowledge/projects/`
   - Person info? → Check `/knowledge/people/`
   - Client details? → Check `/knowledge/clients/`
   - Past decisions? → Check `/knowledge/decisions/`

2. **Search Strategy**
   - First: Glob for exact name matches
   - Second: Grep for mentions across files
   - Third: Read related files for full context

3. **Compile Context Pack**
   - Extract relevant sections
   - Note the source files
   - Flag if information is missing or stale

## Output Format

When returning retrieved context:

```markdown
## Retrieved Context

### From: /knowledge/projects/project-name.md
[Relevant excerpt]

### From: /knowledge/people/person-name.md
[Relevant excerpt]

### Context Gaps
- [Any missing information that should be gathered]

### Sources
- /knowledge/projects/project-name.md
- /knowledge/people/person-name.md
```

## Quality Rules

1. **Always cite sources** — Reference the file paths
2. **Flag stale data** — Note if information seems outdated
3. **Identify gaps** — Call out what's missing
4. **Summarize relevance** — Explain why this context matters for the task

## Example Triggers

- "What's the status of Project Alpha?" → Retrieve project context
- "Prepare for meeting with Sarah" → Retrieve person profile + related projects
- "Draft proposal for Acme Corp" → Retrieve client info + templates
- "What did we decide about the architecture?" → Search decisions
