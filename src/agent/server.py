"""
Web Server for Digital Geoff.

Handles:
- Webhook endpoints for Twilio, Slack, etc.
- Health checks
- Admin API

Uses FastAPI for the HTTP layer.
"""

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from .main import DigitalGeoffApp


# Global app instance
digital_geoff: Optional[DigitalGeoffApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global digital_geoff

    # Startup
    print("Starting Digital Geoff server...")
    digital_geoff = DigitalGeoffApp()
    await digital_geoff.initialize()

    # Start the agent loop in background
    import asyncio
    agent_task = asyncio.create_task(run_agent_background())

    yield

    # Shutdown
    print("Shutting down Digital Geoff server...")
    if digital_geoff:
        await digital_geoff.stop()
    agent_task.cancel()


async def run_agent_background():
    """Run agent loop in background."""
    global digital_geoff
    if digital_geoff and digital_geoff.agent:
        try:
            await digital_geoff.agent.run_loop()
        except Exception as e:
            print(f"Agent loop error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Digital Geoff",
    description="AI Chief of Staff - Autonomous Agent API",
    version="0.1.0",
    lifespan=lifespan
)


# --- Health Check ---

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_running": digital_geoff is not None and digital_geoff._running,
        "tools": digital_geoff.tool_registry.list_tools() if digital_geoff and digital_geoff.tool_registry else [],
        "interfaces": digital_geoff.interface_router.list_channels() if digital_geoff and digital_geoff.interface_router else []
    }


# --- Twilio SMS Webhook ---

@app.post("/webhooks/sms")
async def twilio_sms_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming SMS via Twilio webhook."""
    if not digital_geoff or not digital_geoff.interface_router:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    # Parse form data (Twilio sends form-encoded)
    form_data = await request.form()
    payload = dict(form_data)

    # Get the SMS interface
    sms_interface = digital_geoff.interface_router.get("sms")
    if not sms_interface:
        raise HTTPException(status_code=503, detail="SMS interface not configured")

    # Parse the message
    message = sms_interface._parse_webhook(payload)
    if not message:
        return JSONResponse(content={"status": "ignored"})

    # Process in background
    async def process_message():
        response = await digital_geoff.interface_router._handle_message(message)
        if response:
            await sms_interface.send(response)

    background_tasks.add_task(process_message)

    # Return TwiML response (empty = no immediate reply, we'll send async)
    return JSONResponse(
        content={"status": "processing"},
        media_type="application/json"
    )


# --- Slack Events Webhook ---

@app.post("/webhooks/slack/events")
async def slack_events_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Slack Events API webhook."""
    if not digital_geoff or not digital_geoff.interface_router:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    payload = await request.json()

    # Handle URL verification challenge
    if payload.get("type") == "url_verification":
        return JSONResponse(content={"challenge": payload.get("challenge")})

    # Get the Slack interface
    slack_interface = digital_geoff.interface_router.get("slack")
    if not slack_interface:
        raise HTTPException(status_code=503, detail="Slack interface not configured")

    # Parse the message
    message = slack_interface._parse_webhook(payload)
    if not message:
        return JSONResponse(content={"status": "ignored"})

    # Process in background
    async def process_message():
        response = await digital_geoff.interface_router._handle_message(message)
        if response:
            await slack_interface.send(response)

    background_tasks.add_task(process_message)

    return JSONResponse(content={"status": "processing"})


# --- Slack Slash Commands ---

@app.post("/webhooks/slack/commands")
async def slack_commands_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Slack slash commands."""
    if not digital_geoff or not digital_geoff.interface_router:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    form_data = await request.form()
    payload = dict(form_data)

    # Acknowledge immediately (Slack requires response within 3s)
    # Process in background and use response_url to send result

    async def process_command():
        # Build message from command
        from .interfaces.base import Message, MessagePriority

        message = Message(
            id=payload.get("trigger_id", ""),
            channel="slack",
            sender=payload.get("user_id", ""),
            content=f"{payload.get('command', '')} {payload.get('text', '')}".strip(),
            priority=MessagePriority.HIGH,
            metadata={"response_url": payload.get("response_url")}
        )

        response = await digital_geoff.interface_router._handle_message(message)

        # Send response via response_url
        if response and payload.get("response_url"):
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    payload["response_url"],
                    json={"text": response.content, "response_type": "ephemeral"}
                )

    background_tasks.add_task(process_command)

    # Immediate acknowledgment
    return JSONResponse(content={"response_type": "ephemeral", "text": "Processing..."})


# --- Admin API ---

@app.post("/api/message")
async def send_message(request: Request):
    """Send a message to a specific channel."""
    if not digital_geoff or not digital_geoff.interface_router:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    data = await request.json()
    channel = data.get("channel")
    recipient = data.get("recipient")
    content = data.get("content")

    if not all([channel, content]):
        raise HTTPException(status_code=400, detail="channel and content are required")

    try:
        success = await digital_geoff.interface_router.send(
            channel=channel,
            recipient=recipient or "default",
            content=content
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def query_agent(request: Request):
    """Query the agent directly."""
    if not digital_geoff or not digital_geoff.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    data = await request.json()
    query = data.get("query")

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    try:
        response = await digital_geoff.agent.handle_interrupt(
            message=query,
            source="api"
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status():
    """Get agent status and context."""
    if not digital_geoff or not digital_geoff.agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    return {
        "state": digital_geoff.agent.context.state.value,
        "current_task": digital_geoff.agent.context.current_task,
        "active_projects": digital_geoff.agent.context.active_projects,
        "pending_actions": len(digital_geoff.agent.context.pending_actions),
        "last_checkpoint": digital_geoff.agent.context.last_checkpoint.isoformat() if digital_geoff.agent.context.last_checkpoint else None
    }


# --- Run Server ---

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the web server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
