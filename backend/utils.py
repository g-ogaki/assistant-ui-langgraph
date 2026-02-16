import json
import uuid
from typing import AsyncGenerator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# ── SSE helper ───────────────────────────────────────────────────────────────

def sse(data) -> str:
    """Encode a payload as one Server-Sent Event frame."""
    if isinstance(data, str):
        return f"data: {data}\n\n"
    return f"data: {json.dumps(data)}\n\n"


# ── Core bridge ──────────────────────────────────────────────────────────────

async def langchain_to_vercel_stream(astream_events: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """
    Convert 'agent.astream_events()' to Vercel AI SDK Data Stream Protocol SSE frames.

    Mapping
    -------
    on_chat_model_start   →  start-step
    on_chat_model_stream  →  text-start / text-delta
                              tool-input-start / tool-input-delta
    on_chat_model_end     →  tool-input-available / text-end / finish-step
    on_tool_start         →  start-step   (grouped for parallel calls)
    on_tool_end           →  tool-output-available
    (next on_chat_model_start closes the tool-execution step automatically)
    """

    message_id = f"msg_{uuid.uuid4().hex}"

    # mutable state ----------------------------------------------------------
    step_opened = False
    text_id: str | None = None
    text_block_open = False
    seen_tool_call_ids: set[str] = set()

    # 1) message start -------------------------------------------------------
    yield sse({"type": "start", "messageId": message_id})

    try:
        async for event in astream_events:
            ev = event["event"]

            # ── LLM invocation starts ────────────────────────────────
            if ev == "on_chat_model_start":
                # Close a previous step that is still open
                # (e.g. the tool-execution step).
                if step_opened:
                    yield sse({"type": "finish-step"})
                yield sse({"type": "start-step"})
                step_opened = True

            # ── Streaming tokens / tool-call argument chunks ─────────
            elif ev == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                content: str = getattr(chunk, "content", "") or ""
                tc_chunks: list = getattr(chunk, "tool_call_chunks", None) or []

                # ▸ text delta
                if content:
                    if not text_block_open:
                        text_id = f"text_{uuid.uuid4().hex}"
                        yield sse({"type": "text-start", "id": text_id})
                        text_block_open = True
                    yield sse({
                        "type": "text-delta",
                        "id": text_id,
                        "delta": content,
                    })

                # ▸ tool-call argument streaming
                for tc in tc_chunks:
                    tc_id = (tc["id"] if isinstance(tc, dict)
                             else getattr(tc, "id", None))
                    tc_name = (tc.get("name") if isinstance(tc, dict)
                               else getattr(tc, "name", None))
                    tc_args = (tc.get("args", "") if isinstance(tc, dict)
                               else getattr(tc, "args", ""))
                    if not tc_id:
                        continue

                    # first chunk for this call → announce it
                    if tc_id not in seen_tool_call_ids:
                        seen_tool_call_ids.add(tc_id)
                        yield sse({
                            "type": "tool-input-start",
                            "toolCallId": tc_id,
                            "toolName": tc_name or "",
                        })

                    # stream the argument JSON fragment
                    if tc_args:
                        yield sse({
                            "type": "tool-input-delta",
                            "toolCallId": tc_id,
                            "inputTextDelta": tc_args,
                        })

            # ── LLM invocation ends ──────────────────────────────────
            elif ev == "on_chat_model_end":
                output = event["data"]["output"]

                # close an open text block
                if text_block_open and text_id:
                    yield sse({"type": "text-end", "id": text_id})
                    text_block_open = False
                    text_id = None

                # finalise every tool call the model proposed
                for tc in getattr(output, "tool_calls", None) or []:
                    tc_id = tc["id"]
                    tc_name = tc["name"]
                    tc_input = tc["args"]        # already a dict

                    # If the provider never streamed argument chunks
                    # (non-streaming / batch provider), emit start + delta
                    # so the frontend has the full picture.
                    if tc_id not in seen_tool_call_ids:
                        seen_tool_call_ids.add(tc_id)
                        yield sse({
                            "type": "tool-input-start",
                            "toolCallId": tc_id,
                            "toolName": tc_name,
                        })
                        yield sse({
                            "type": "tool-input-delta",
                            "toolCallId": tc_id,
                            "inputTextDelta": json.dumps(tc_input),
                        })

                    yield sse({
                        "type": "tool-input-available",
                        "toolCallId": tc_id,
                        "toolName": tc_name,
                        "input": tc_input,
                    })

                if step_opened:
                    yield sse({"type": "finish-step"})
                    step_opened = False

            # ── Tool execution starts ────────────────────────────────
            elif ev == "on_tool_start":
                # Open ONE step for all tool executions in this graph
                # node (handles parallel tool calls).
                if not step_opened:
                    yield sse({"type": "start-step"})
                    step_opened = True

            # ── Tool execution ends ──────────────────────────────────
            elif ev == "on_tool_end":
                tool_msg = event["data"]["output"]
                tc_id: str = getattr(tool_msg, "tool_call_id", "")
                raw_content = getattr(tool_msg, "content", "")

                if not isinstance(raw_content, str):
                    raw_content = json.dumps(raw_content)

                # try to deserialise structured output
                try:
                    output_val = json.loads(raw_content)
                except (json.JSONDecodeError, TypeError):
                    output_val = raw_content

                yield sse({
                    "type": "tool-output-available",
                    "toolCallId": tc_id,
                    "output": output_val,
                })
                # Step stays open – it will be closed by the next
                # on_chat_model_start or by the cleanup below.

    except Exception as exc:
        yield sse({"type": "error", "errorText": str(exc)})

    # 2) clean up anything still open ----------------------------------------
    if text_block_open and text_id:
        yield sse({"type": "text-end", "id": text_id})
    if step_opened:
        yield sse({"type": "finish-step"})

    # 3) message finish -------------------------------------------------------
    yield sse({"type": "finish"})
    yield sse("[DONE]")