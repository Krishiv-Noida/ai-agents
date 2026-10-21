"""
Django views for agent orchestration and streaming interaction.
"""
import json
import uuid
from typing import AsyncGenerator
from django.http import HttpRequest, StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from langchain_core.messages import HumanMessage

from orchestration_app.graph.workflow import app


@csrf_exempt
async def orchestrate_chat(request: HttpRequest) -> StreamingHttpResponse:
    """
    Async Django view handling multi-agent orchestration via LangGraph.
    
    Accepts:
        POST JSON payload:
        {
            "message": "Write a Python function to compute primes.",
            "thread_id": "optional-session-uuid"
        }
        
    Streams:
        Server-Sent Events (SSE) chunks yielding supervisor routing decisions,
        worker outputs, and final artifacts in real time.
    """
    if request.method != "POST":
        return JsonResponse(
            {"error": "Method Not Allowed. Please send a POST request."}, 
            status=405
        )

    try:
        body = request.body.decode("utf-8") if request.body else "{}"
        payload = json.loads(body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload in request body."}, status=400)

    user_message = payload.get("message")
    if not user_message or not isinstance(user_message, str):
        return JsonResponse(
            {"error": "Missing or invalid 'message' field in JSON request."}, 
            status=400
        )

    # Use provided thread_id or generate a fresh thread session
    thread_id = str(payload.get("thread_id") or uuid.uuid4())

    # Build initial LangGraph inputs
    inputs = {
        "messages": [HumanMessage(content=user_message)],
        "next_worker": "",
        "worker_outputs": {},
    }
    config = {"configurable": {"thread_id": thread_id}}

    async def event_stream() -> AsyncGenerator[str, None]:
        """Asynchronously streams workflow execution chunks as SSE data packets."""
        # Initial metadata event
        yield f"data: {json.dumps({'event': 'started', 'thread_id': thread_id})}\n\n"

        try:
            # Stream updates from the compiled graph using astream
            async for chunk in app.astream(inputs, config=config, stream_mode="updates"):
                # chunk is a dictionary mapping {node_name: node_state_update}
                for node_name, node_update in chunk.items():
                    # Format message contents for the client
                    serialized_messages = []
                    for msg in node_update.get("messages", []):
                        if hasattr(msg, "content"):
                            msg_role = getattr(msg, "name", None) or msg.__class__.__name__
                            content = msg.content
                            if isinstance(content, list):
                                parts = [
                                    p.get("text", "") if isinstance(p, dict) else str(p)
                                    for p in content
                                ]
                                content = "".join(parts)
                            serialized_messages.append({
                                "sender": msg_role,
                                "content": content
                            })
                        else:
                            serialized_messages.append({
                                "sender": node_name,
                                "content": str(msg)
                            })

                    event_payload = {
                        "event": "node_update",
                        "node": node_name,
                        "next_worker": node_update.get("next_worker"),
                        "worker_outputs": node_update.get("worker_outputs"),
                        "messages": serialized_messages,
                    }
                    yield f"data: {json.dumps(event_payload)}\n\n"

            # Completion event
            yield f"data: {json.dumps({'event': 'completed', 'thread_id': thread_id})}\n\n"

        except Exception as exc:
            error_payload = {
                "event": "error",
                "error": str(exc),
                "thread_id": thread_id
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    response = StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream"
    )
    # Recommended streaming headers to avoid proxy buffering
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
