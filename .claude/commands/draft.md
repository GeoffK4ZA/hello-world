---
name: Draft
description: Draft an email, message, or document in Geoff's voice
argument-hint: <type> <context or paste content>
allowed-tools: Read, Glob, Write
---

# Draft

Create a draft: **$ARGUMENTS**

## Supported Types
- `email` — Professional email
- `slack` — Slack/Teams message
- `update` — Status update or announcement
- `response` — Reply to something (paste the original)
- `doc` — Short document or memo

## Process

1. **Understand the Request**
   - What type of communication?
   - Who is the audience?
   - What's the objective?
   - What tone is appropriate?

2. **Gather Context**
   - Check `/knowledge/people/` for recipient context
   - Check `/knowledge/projects/` for relevant background
   - Review templates in `/knowledge/templates/` if applicable

3. **Draft in Geoff's Voice**
   - Direct and clear
   - Professional but human
   - Gets to the point quickly
   - Ends with clear next steps or ask

4. **Generate Draft**

## Output Format

```markdown
# Draft: [TYPE]
**To**: [Recipient]
**Subject/Topic**: [Subject line or topic]
**Objective**: [What this should achieve]

---

## Draft

[The actual draft content]

---

## Notes
- **Tone**: [Formal/Casual/Urgent]
- **Key point to land**: [Main message]
- **Attachments needed**: [If any]

## Before Sending
- [ ] Check recipient is correct
- [ ] Verify any numbers/dates
- [ ] Confirm tone is appropriate
```

5. **Save Draft**
   - Save to `/artefacts/drafts/[DATE]_[type]_[slug].md`

6. **Return Draft**
   - Return the draft for review
   - Ask for approval before any sending action
   - Offer to refine if needed

## Geoff's Writing Style

- **Openings**: No "I hope this email finds you well" — get to the point
- **Structure**: Lead with the ask or key info, then context
- **Tone**: Confident, competent, approachable
- **Closings**: Clear next step or call to action
- **Length**: As short as possible while being complete
