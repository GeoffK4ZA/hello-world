# Geoff OS Setup Guide

Complete setup instructions to get your Digital Chief of Staff operational.

**Time Required:** ~30 minutes for basic setup, ~1 hour for full configuration

---

## Prerequisites

- [x] Claude Code CLI installed
- [x] Claude Max subscription (for $0 operation)
- [ ] Telegram account
- [ ] (Optional) Asana account
- [ ] (Optional) Google Workspace account

---

## Phase 1: Basic Setup (5 minutes)

### 1.1 Verify Claude Code Works

```bash
# Test Claude Code is working
cd /path/to/hello-world
claude --version

# Start Claude Code in this directory
claude
```

You should see Claude Code start with access to the CLAUDE.md context.

### 1.2 Test Commands

Inside Claude Code, try:
```
/brief
/status all
```

These will work but return limited results until you populate your knowledge base.

---

## Phase 2: Telegram Bot Setup (10 minutes)

This gives you mobile access to Geoff OS.

### 2.1 Create Your Bot

1. Open Telegram and message **@BotFather**
2. Send `/newbot`
3. Follow the prompts:
   - Name: `Geoff OS` (or whatever you want)
   - Username: `your_geoff_bot` (must end in `bot`)
4. **Copy the token** — looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### 2.2 Get Your User ID

1. Message **@userinfobot** on Telegram
2. It will reply with your user ID
3. **Copy your user ID** — looks like: `123456789`

### 2.3 Configure Environment

Create a file or add to your shell profile:

```bash
# Add to ~/.bashrc or ~/.zshrc
export TELEGRAM_BOT_TOKEN="your-bot-token-here"
export TELEGRAM_ALLOWED_USERS="your-user-id-here"
```

Then reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

### 2.4 Install Dependencies

```bash
cd /path/to/hello-world
pip install python-telegram-bot
```

### 2.5 Run the Bot

```bash
python integrations/telegram/bot.py
```

You should see:
```
Starting Geoff OS Telegram Bot...
Authorized users: [123456789]
Bot is running. Press Ctrl+C to stop.
```

### 2.6 Test It

1. Open Telegram
2. Find your bot (search for the username you created)
3. Send `/start`
4. Try `/brief` or just ask a question

**Keep the bot running** in a terminal or set up as a service (see Advanced Setup).

---

## Phase 3: Populate Knowledge Base (15 minutes)

This is what makes Geoff OS actually useful — your context.

### 3.1 Add Your Projects

For each active project, create a file:

```bash
cp knowledge/templates/project-template.md knowledge/projects/my-project.md
```

Edit the file with your project details. Example:

```markdown
# Project: Data Platform Migration

## Quick Facts
- **Status**: 🟡 In Progress
- **Priority**: High
- **Started**: 2025-12-01
- **Target Completion**: 2026-03-31
- **Owner**: Geoff

## Overview
Migrating legacy data warehouse to modern cloud-based platform.

## Key Stakeholders
- Sarah Chen (VP Engineering) - Executive sponsor
- Mike Johnson (Tech Lead) - Technical decisions
- Finance Team - End users

## Current Status
Phase 2 of 4 complete. Currently working on data transformation layer.

## Blockers
- Waiting on API access from vendor (escalated 2026-01-10)

## Next Actions
- [ ] Complete transformation scripts
- [ ] Schedule UAT with Finance
- [ ] Prepare go-live checklist

## Key Decisions
- 2025-12-15: Chose Snowflake over BigQuery (cost + existing skills)
- 2026-01-05: Delayed go-live by 2 weeks for additional testing

## Notes
Weekly sync every Tuesday 10am with Sarah.
```

### 3.2 Add Key People

For important stakeholders, create profiles:

```bash
cp knowledge/templates/person-template.md knowledge/people/sarah-chen.md
```

Example:

```markdown
# Sarah Chen

## Role
VP Engineering at TechCorp

## Relationship
Executive sponsor for Data Platform project. Direct relationship since 2024.

## Communication Style
- Prefers: Concise updates, data-driven arguments
- Avoid: Long emails, too much technical detail
- Best channel: Slack for quick items, email for decisions

## Context
- Reports to CTO
- Has budget authority up to $500K
- Very focused on delivery timelines
- Promoted from Director in Q3 2025

## Recent Interactions
- 2026-01-10: Discussed timeline concerns, agreed to 2-week buffer
- 2026-01-05: Presented Phase 1 results, positive feedback

## Notes
Birthday: March 15. Coffee preference: Flat white.
```

### 3.3 Add Clients (If Applicable)

```bash
cp knowledge/templates/client-template.md knowledge/clients/acme-corp.md
```

### 3.4 Set Up Active Tasks

Edit the active tasks file:

```bash
nano knowledge/tasks/active_tasks.md
```

Add your current tasks:

```markdown
# Active Tasks

## High Priority
- [ ] Complete API integration for Project Alpha (Due: Jan 15)
- [ ] Review proposal for Acme Corp (Due: Jan 14)

## Medium Priority
- [ ] Update documentation for onboarding
- [ ] Schedule Q1 planning sessions

## Low Priority / Backlog
- [ ] Research new testing frameworks
- [ ] Clean up old project files

## Waiting On
- [ ] API access from vendor (escalated Jan 10)
- [ ] Budget approval from Finance

---
*Last updated: 2026-01-12*
```

---

## Phase 4: Optional Integrations

### 4.1 Asana Integration

If you use Asana for task management:

**Get Token:**
1. Go to https://app.asana.com/0/my-apps
2. Create a Personal Access Token
3. Copy the token

**Configure:**
```bash
export ASANA_ACCESS_TOKEN="your-asana-token"
```

**Enable in settings:**
Edit `.claude/settings.json`:
```json
"asana": {
  ...
  "disabled": false
}
```

### 4.2 Google Calendar Integration

If you use Google Calendar:

**Setup Service Account:**
1. Go to Google Cloud Console
2. Create a new project (or use existing)
3. Enable Calendar API
4. Create Service Account credentials
5. Download the JSON key file
6. Share your calendar with the service account email

**Configure:**
```bash
export GOOGLE_CREDENTIALS_PATH="/path/to/your-credentials.json"
```

**Enable in settings:**
Edit `.claude/settings.json`:
```json
"google-calendar": {
  ...
  "disabled": false
}
```

### 4.3 Scheduled Tasks

To enable automatic scheduled tasks (morning briefs, etc.):

**Install ClaudeCron:**
```bash
npm install -g claudecron
```

**Enable in settings:**
Edit `.claude/settings.json`:
```json
"scheduler": {
  ...
  "disabled": false
}
```

**Configure schedules:**
Edit `integrations/scheduler/schedules.json` to adjust times/enable tasks.

---

## Phase 5: Advanced Setup

### 5.1 Run Telegram Bot as Service (Linux)

Create systemd service:

```bash
sudo nano /etc/systemd/system/geoff-telegram.service
```

```ini
[Unit]
Description=Geoff OS Telegram Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/hello-world
Environment="TELEGRAM_BOT_TOKEN=your-token"
Environment="TELEGRAM_ALLOWED_USERS=your-user-id"
ExecStart=/usr/bin/python3 integrations/telegram/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable geoff-telegram
sudo systemctl start geoff-telegram
```

Check status:
```bash
sudo systemctl status geoff-telegram
```

### 5.2 Run on macOS (launchd)

Create plist file:
```bash
nano ~/Library/LaunchAgents/com.geoff.telegram.plist
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.geoff.telegram</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/hello-world/integrations/telegram/bot.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TELEGRAM_BOT_TOKEN</key>
        <string>your-token</string>
        <key>TELEGRAM_ALLOWED_USERS</key>
        <string>your-user-id</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>/path/to/hello-world</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.geoff.telegram.plist
```

---

## Quick Reference

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | For Telegram | Bot token from @BotFather |
| `TELEGRAM_ALLOWED_USERS` | For Telegram | Your Telegram user ID |
| `ASANA_ACCESS_TOKEN` | For Asana | Personal access token |
| `GOOGLE_CREDENTIALS_PATH` | For Calendar | Path to service account JSON |

### Commands Available

| Command | Description |
|---------|-------------|
| `/brief` | Daily operating brief |
| `/prep <meeting>` | Meeting preparation |
| `/task <description>` | Capture a task |
| `/status <project>` | Project status |
| `/draft <type>` | Draft communication |

### File Locations

| What | Where |
|------|-------|
| Projects | `knowledge/projects/*.md` |
| People | `knowledge/people/*.md` |
| Clients | `knowledge/clients/*.md` |
| Tasks | `knowledge/tasks/active_tasks.md` |
| Templates | `knowledge/templates/*.md` |
| Outputs | `artefacts/` |
| Config | `.claude/settings.json` |

---

## Checklist

### Minimum Viable Setup
- [ ] Claude Code working
- [ ] At least one project in `knowledge/projects/`
- [ ] Active tasks in `knowledge/tasks/active_tasks.md`

### Recommended Setup
- [ ] Telegram bot configured and running
- [ ] 3-5 key people in `knowledge/people/`
- [ ] All active projects documented
- [ ] Preferences started in `knowledge/preferences/`

### Full Setup
- [ ] All integrations enabled (Asana, Calendar)
- [ ] Scheduled tasks configured
- [ ] Telegram bot running as service
- [ ] Knowledge base fully populated

---

## Troubleshooting

### Telegram bot not responding
```bash
# Check if running
ps aux | grep telegram

# Check logs
python integrations/telegram/bot.py  # Run manually to see errors
```

### Claude Code not finding context
```bash
# Make sure you're in the right directory
cd /path/to/hello-world
claude

# Check CLAUDE.md is present
cat CLAUDE.md
```

### Commands returning generic responses
- Add more context to your knowledge base
- Make sure project/people files have actual content
- Check that file paths in CLAUDE.md match your structure

---

## Getting Help

- **Claude Code docs**: https://code.claude.com/docs
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **This repo**: Check integrations/README.md for detailed integration docs

---

*Setup guide version 1.0 — Last updated: 2026-01-12*
