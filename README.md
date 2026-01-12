# Digital Geoff

> Autonomous AI Agent — Virtual Chief of Staff + Solution/Data Architect Partner

An intelligent digital twin that runs 24/7, managing your calendar, tasks, communications, and strategic work. Not simple automations — a full agent system with persistent memory, knowledge graphs, and multi-channel interfaces.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DIGITAL GEOFF AGENT CORE                         │
│                     Claude (Opus/Sonnet) + Tool Use                     │
├─────────────────────────────────────────────────────────────────────────┤
│   MEMORY LAYER        │   KNOWLEDGE GRAPH      │   ACTION LAYER        │
│   • Episodic          │   • Projects           │   • Outlook/Teams     │
│   • Semantic          │   • People             │   • Asana             │
│   • Procedural        │   • Decisions          │   • Slack             │
│   • Working           │   • Relationships      │   • Google Sheets     │
├─────────────────────────────────────────────────────────────────────────┤
│                    DURABLE EXECUTION + CHECKPOINTING                    │
├─────────────────────────────────────────────────────────────────────────┤
│   SMS (Twilio)    │   Slack Bot    │   Teams Bot    │   Webhooks       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Features

- **Persistent Memory**: Remembers conversations, decisions, and preferences across sessions
- **Knowledge Graph**: Maintains relationships between projects, people, and decisions
- **Multi-Channel Interface**: Interact via SMS, Slack, Teams, or API
- **Durable Execution**: Checkpoints after each step, recovers from failures
- **Tool Integration**: Microsoft 365, Asana, Slack, Google Sheets, Notion, GitHub
- **Proactive Operation**: Morning briefings, meeting prep, stale task alerts

## Quick Start

### 1. Clone and Configure

```bash
git clone https://github.com/GeoffK4ZA/hello-world.git
cd hello-world
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run with Docker

```bash
docker-compose up -d
```

### 3. Test the Agent

```bash
# Check health
curl http://localhost:8000/health

# Query the agent
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are my priorities today?"}'
```

## Project Structure

```
src/agent/
├── core.py           # Main agent with reasoning loop
├── memory.py         # Multi-tier memory system (episodic, semantic, procedural)
├── knowledge.py      # Knowledge graph for projects, people, decisions
├── execution.py      # Durable execution with checkpointing
├── main.py           # Application entry point
├── server.py         # FastAPI server for webhooks
├── tools/            # Tool integrations
│   ├── microsoft365.py   # Outlook, Teams
│   ├── asana.py          # Task management
│   ├── slack.py          # Messaging
│   ├── twilio.py         # SMS
│   ├── google.py         # Sheets, Slides
│   ├── notion.py         # Knowledge base
│   └── github.py         # Code management
└── interfaces/       # Communication interfaces
    ├── sms.py            # Twilio SMS
    └── slack_interface.py # Slack Events API

n8n/                  # N8N workflow exports
├── morning_briefing.json
├── meeting_prep.json
└── post_meeting_actions.json
```

## Required Credentials

| Service | Required | How to Get |
|---------|----------|------------|
| **Anthropic** | Yes | [console.anthropic.com](https://console.anthropic.com) |
| **Microsoft 365** | Recommended | Azure AD App Registration |
| **Asana** | Recommended | Personal Access Token |
| **Slack** | Recommended | Slack App with Bot Token |
| **Twilio** | Optional | SMS-capable phone number |
| **Google** | Optional | Service Account credentials |
| **Notion** | Optional | Integration token |
| **GitHub** | Optional | Personal Access Token |

See `.env.example` for full configuration details.

## SMS Commands

Text these commands to your Twilio number:

| Command | Description |
|---------|-------------|
| `status` | Get current priority stack |
| `tasks` | Get today's Asana tasks |
| `prep <meeting>` | Get meeting prep |
| `block 2h tomorrow` | Block strategic time |
| `note <text>` | Store a quick note |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/query` | POST | Query the agent |
| `/api/status` | GET | Get agent status |
| `/api/message` | POST | Send message to channel |
| `/webhooks/sms` | POST | Twilio webhook |
| `/webhooks/slack/events` | POST | Slack Events API |
| `/webhooks/slack/commands` | POST | Slack slash commands |

## N8N Integration

Import the workflows from `n8n/` directory:

1. **Morning Briefing** - Daily 6:30 AM summary
2. **Meeting Prep** - Auto-generates prep 2 hours before meetings
3. **Post-Meeting Actions** - Extracts action items and creates tasks

Set these N8N environment variables:
- `DIGITAL_GEOFF_URL` - Your deployment URL
- `USER_EMAIL` - Your email for notifications
- `SLACK_DM_CHANNEL` - Slack channel for notifications

## Deployment Options

### Docker Compose (Self-Hosted)

```bash
docker-compose up -d
```

Includes Redis (memory), Neo4j (knowledge graph), and Qdrant (vectors).

### Cloud Run (Google Cloud)

```bash
gcloud run deploy digital-geoff \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Railway

```bash
railway up
```

## Memory System

Digital Geoff uses a multi-tier memory system:

| Type | What It Stores | Use Case |
|------|----------------|----------|
| **Episodic** | Past conversations, actions | "What did we decide about X?" |
| **Semantic** | Facts about projects, people | "Who is Sarah Chen?" |
| **Procedural** | How things are done | "How do I like status reports?" |
| **Working** | Current session context | Active task tracking |

## Knowledge Graph

Entities and relationships are tracked:

```
[You] ─── works_on ───► [Project: Data Platform]
                              │
                              ├── has_stakeholder ──► [Sarah Chen]
                              ├── blocked_by ──► [API access pending]
                              └── deadline ──► [2026-01-20]
```

This enables contextual reasoning like: *"Meeting with Sarah in 2 hours. She's on the Data Platform project which is blocked by API access. I should prep talking points on that."*

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m src.agent.main --run

# Run tests
pytest

# Type checking
mypy src/
```

## Resources

- [Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Mem0 - AI Agent Memory](https://arxiv.org/abs/2504.19413)
- [Cognee - Knowledge Graphs](https://github.com/topoteretes/cognee)
- [LangGraph Durable Execution](https://docs.langchain.com/langgraph-platform)

---

*Version 0.1.0 | Established 2026-01-12*
