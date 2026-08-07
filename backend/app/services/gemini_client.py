import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_env_paths = [
    Path(__file__).resolve().parents[2] / ".env",
    Path(__file__).resolve().parents[3] / ".env",
]
for _path in _env_paths:
    if _path.exists():
        load_dotenv(dotenv_path=_path)
        break

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("[Gemini] GEMINI_API_KEY missing; AI pipeline will fall back to rule-based logic.")
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as exc:
        logger.error(f"[Gemini] client init failed: {exc}")
        return None


def parse_json_response(text):
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except (ValueError, TypeError):
        return None


def generate_json(system_prompt, user_prompt, temperature=0.2, max_retries=2):
    client = get_gemini_client()
    if client is None:
        return None
    contents = f"{system_prompt}\n\n{user_prompt}"
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=temperature,
                )
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=contents,
                    config=config,
                )
            except Exception:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=contents,
                )
            data = parse_json_response(getattr(response, "text", None) or "")
            if data is not None:
                return data
            last_error = "empty or non-JSON response"
        except Exception as exc:
            last_error = str(exc)
            logger.warning(f"[Gemini] generate_json attempt {attempt + 1} failed: {exc}")
    logger.warning(f"[Gemini] generate_json exhausted retries: {last_error}")
    return None


def generate_content_with_tools(
    system_prompt,
    user_prompt,
    tools,
    execute_tool,
    max_turns=5,
    temperature=0.2,
):
    """
    Agentic tool-calling loop.

    The LLM decides (based on its system prompt) which tools from `tools` to
    invoke. Each time it requests a tool call, `execute_tool(name, args)` runs it
    and the result is fed back into the conversation. The loop terminates when the
    model produces a final text answer (e.g. structured JSON) without further calls.

    Args:
        system_prompt: instruction describing the agent persona & tools.
        user_prompt: the initial task/message.
        tools: list of python functions to expose as Gemini FunctionDeclarations.
        execute_tool: callable(name: str, args: dict) -> anything (stringified to model).
        max_turns: cap on tool-call rounds to prevent runaway loops.
        temperature: generation temperature.

    Returns:
        The model's final text (string) or None on repeated failure.
    """
    client = get_gemini_client()
    if client is None:
        logger.warning("[Gemini] tools loop skipped: no client available.")
        return None

    try:
        from google.genai import types
    except Exception as exc:
        logger.error(f"[Gemini] Could not import genai types: {exc}")
        return None

    # Build FunctionDeclarations + a Tool from the provided python callables.
    declarations = []
    name_to_func = {}
    for fn in tools:
        name = fn.__name__
        name_to_func[name] = fn
        import inspect
        sig = inspect.signature(fn)
        params = _param_schema(sig)
        declarations.append(
            types.FunctionDeclaration(
                name=name,
                description=(fn.__doc__ or "").strip()[:500],
                parameters=params,
            )
        )

    tool_config = types.Tool(function_declarations=declarations)

    first_user_turn = types.Content(
        role="user",
        parts=[types.Part(text=(
            f"{system_prompt}\n\nAVAILABLE TOOLS (call only when you need them):\n"
            + "\n".join(f"- {fn.__name__}: {(fn.__doc__ or 'n/a').strip()}" for fn in tools)
            + "\n\nWhen you are done, respond with your final answer directly (plain text)."
            f"\n\nUSER TASK:\n{user_prompt}"
        ))],
    )
    contents = [first_user_turn]
    last_error = None
    already_submitted = False  # avoid re-submitting the init user turn after a completed loop

    for _ in range(max_turns):
        try:
            config = types.GenerateContentConfig(
                tools=[tool_config],
                temperature=temperature,
            )
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            last_error = str(exc)
            logger.warning(f"[Gemini] tool-turn generation failed: {exc}")
            break

        function_calls = []
        if not response.candidates:
            logger.warning("[Gemini] tool-turn response has no candidates (safety filter or empty response). Breaking loop.")
            break
        candidate_content = response.candidates[0].content
        for part in candidate_content.parts:
            if part.function_call is not None:
                function_calls.append(part.function_call)

        if function_calls:
            # Append the model's own response (it carries function_call + thought_signature)
            contents.append(candidate_content)
            tool_result_parts = []
            for fc in function_calls:
                name = fc.name
                args = dict(fc.args or {})
                logger.info(f"[Gemini] Agent requested tool call: {name}({args})")
                try:
                    result = execute_tool(name, args)
                    response_text = str(result)
                except Exception as exc:
                    response_text = f"ERROR: {exc}"
                    logger.error(f"[Gemini] Tool execution error for {name}: {exc}")
                tool_result_parts.append(
                    types.Part(function_response=types.FunctionResponse(
                        name=name,
                        response={"result": response_text},
                    ))
                )
            contents.append(
                types.Content(role="user", parts=tool_result_parts)
            )
            continue  # model continues now that tools returned

        # No tool calls → the model produced a final answer (or an empty response).
        text_parts = candidate_content.parts
        full_text = "".join((p.text or "") for p in text_parts if getattr(p, "text", None))
        if full_text.strip():
            return full_text.strip()

        # Model returned no function calls AND no text — nudge it to produce its final answer
        logger.warning("[Gemini] Model turn had no function calls and no text. Sending final-answer nudge.")
        contents.append(candidate_content)
        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=(
                "You have received all tool results. "
                "Now provide your final answer as a single JSON object only. "
                "No markdown, no explanation, just the JSON."
            ))],
        ))

    logger.warning(f"[Gemini] tool-calling loop exhausted turns (last_error={last_error})")
    return None


def _param_schema(sig):
    """Build a minimal JSON schema from inspect.Signature for FunctionDeclaration."""
    from google.genai import types
    props = {}
    required = []
    for name, param in sig.parameters.items():
        if param.kind in (param.POSITIONAL_ONLY, param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        props[name] = types.Schema(type="STRING")
        if param.default is param.empty:
            required.append(name)
    schema = {"type": "OBJECT", "properties": props}
    if required:
        schema["required"] = required
    return types.Schema(**schema)
