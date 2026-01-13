# Geoff OS Integrations

Phase 2: External interfaces and scheduled execution.

## Components

### 1. Telegram Bot (`telegram/`)

Mobile interface to Geoff OS via Telegram.

**Setup:**
```bash
# 1. Create bot via @BotFather on Telegram
#    - Send /newbot
#    - Follow prompts
#    - Copy the token

# 2. Get your user ID
#    - Message @userinfobot on Telegram
#    - Copy your user ID

# 3. Set environment variables
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_ALLOWED_USERS="your-user-id"

# 4. Install dependencies
pip install python-telegram-bot

# 5. Run the bot
python integrations/telegram/bot.py
```

**Commands:**
| Command | Description |
|---------|-------------|
| `/brief` | Daily operating brief |
| `/prep <meeting>` | Meeting preparation |
| `/task <description>` | Capture a task |
| `/status <project>` | Project status |
| `/draft <type>` | Draft communication |

Or send any message for free-form queries.

---

### 2. Scheduler (`scheduler/`)

Scheduled task execution using ClaudeCron MCP.

**Configured Schedules:**

| Schedule | When | What |
|----------|------|------|
| Morning Brief | 6:30 AM Mon-Fri | Generate daily brief |
| Weekly Consolidation | 7:00 AM Monday | Run memory consolidator |
| Evening Summary | 5:00 PM Mon-Fri | Day summary (disabled) |
| Stale Task Check | 9:00 AM Mon-Fri | Flag old tasks (disabled) |

**Enable Scheduler:**
```bash
# Install ClaudeCron MCP
npm install -g claudecron

# Edit .claude/settings.json
# Set scheduler.disabled = false

# Schedules are in integrations/scheduler/schedules.json
```

---

### 3. MCP Servers (configured in `.claude/settings.json`)

| Server | Purpose | Status |
|--------|---------|--------|
| `filesystem` | Read/write knowledge and artefacts | Enabled |
| `asana` | Task management sync | Disabled (needs token) |
| `google-calendar` | Calendar awareness | Disabled (needs credentials) |
| `scheduler` | Scheduled execution | Disabled |

**Enable Asana:**
```bash
# 1. Get Personal Access Token from Asana
#    https://app.asana.com/0/my-apps

# 2. Set environment variable
export ASANA_ACCESS_TOKEN="your-token"

# 3. Edit .claude/settings.json
#    Set asana.disabled = false
```

**Enable Google Calendar:**
```bash
# 1. Create service account in Google Cloud Console
# 2. Enable Calendar API
# 3. Download credentials JSON

# 4. Set environment variable
export GOOGLE_CREDENTIALS_PATH="/path/to/credentials.json"

# 5. Edit .claude/settings.json
#    Set google-calendar.disabled = false
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐                │
│   │ Telegram │    │  Claude  │    │ Scheduler│                │
│   │   Bot    │    │   CLI    │    │  (Cron)  │                │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘                │
│        │               │               │                       │
│        └───────────────┼───────────────┘                       │
│                        ▼                                       │
│              ┌─────────────────┐                               │
│              │    Claude Code   │                               │
│              │   (Geoff OS)    │                               │
│              └────────┬────────┘                               │
│                       │                                        │
│        ┌──────────────┼──────────────┐                        │
│        ▼              ▼              ▼                         │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐                     │
│   │  Asana  │   │Calendar │   │  Files  │                     │
│   │   MCP   │   │   MCP   │   │   MCP   │                     │
│   └─────────┘   └─────────┘   └─────────┘                     │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Running Everything

### Quick Start (Telegram Only)

```bash
# Terminal 1: Run Telegram bot
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_ALLOWED_USERS="..."
python integrations/telegram/bot.py

# Use: Message your bot on Telegram
```

### Full Setup (All Integrations)

```bash
# 1. Set all environment variables
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_ALLOWED_USERS="..."
export ASANA_ACCESS_TOKEN="..."
export GOOGLE_CREDENTIALS_PATH="..."

# 2. Enable MCP servers in .claude/settings.json

# 3. Run Telegram bot
python integrations/telegram/bot.py &

# 4. Use Claude Code normally - MCP servers activate automatically
claude
```

---

## Hooks

The `.claude/settings.json` configures automatic behaviors:

**SessionStart:**
- Loads today's context from active tasks
- Prepares Claude with current state

**Stop:**
- Prompts to save learnings from the interaction
- Reminds to save artefacts if created

---

## Customization

### Add New Scheduled Task

Edit `integrations/scheduler/schedules.json`:
```json
{
  "name": "my-task",
  "description": "What it does",
  "cron": "0 9 * * *",
  "prompt": "Your prompt here",
  "enabled": true
}
```

### Add New MCP Server

Edit `.claude/settings.json`:
```json
{
  "mcp": {
    "servers": {
      "my-server": {
        "command": "npx",
        "args": ["-y", "@org/mcp-server-name"],
        "disabled": false
      }
    }
  }
}
```
