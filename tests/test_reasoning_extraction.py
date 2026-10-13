"""Tests for surfacing `reasoning_content` from OpenAI-compatible servers
(Unsloth Studio / llama.cpp / vLLM) through ChatOpenAIWithReasoning."""
import core_engine
from langchain_core.messages import AIMessageChunk


def _make_llm(**cfg_overrides):
    cfg = {"api_key": "test-key", "api_base": "http://localhost:9999/v1", "model": "test-model"}
    cfg.update(cfg_overrides)
    return core_engine.setup_llm(cfg)


def _chunk(delta):
    return {"id": "x", "model": "test-model", "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}


def _extract_like_generation_thread(chunk):
    """Mirror of the reasoning/content split in generation_thread.py."""
    reasoning = chunk.additional_kwargs.get("reasoning_content", "")
    content_str = ""
    if hasattr(chunk, "content_blocks") and isinstance(chunk.content_blocks, list):
        for block in chunk.content_blocks:
            if isinstance(block, dict):
                if block.get("type") == "reasoning":
                    reasoning += block.get("reasoning", "")
                elif block.get("type") == "text":
                    content_str += block.get("text", "")
    return reasoning, content_str


def test_llm_is_reasoning_subclass():
    llm = _make_llm()
    assert isinstance(llm, core_engine.ChatOpenAIWithReasoning)


def test_extra_body_has_enable_thinking_and_no_bogus_keys():
    llm = _make_llm()
    body = llm.extra_body
    assert body["chat_template_kwargs"] == {"enable_thinking": True}
    assert "includereasoning" not in body
    assert "reasoning" not in body


def test_enable_thinking_can_be_disabled():
    llm = _make_llm(enable_thinking=False)
    assert llm.extra_body["chat_template_kwargs"] == {"enable_thinking": False}


def test_reasoning_effort_omitted_by_default():
    llm = _make_llm()
    assert "reasoning_effort" not in llm.extra_body["chat_template_kwargs"]


def test_reasoning_effort_from_config():
    llm = _make_llm(reasoning_effort="high")
    assert llm.extra_body["chat_template_kwargs"]["reasoning_effort"] == "high"


def test_reasoning_effort_agent_overrides_config():
    cfg = {"api_key": "k", "api_base": "http://localhost:9999/v1", "reasoning_effort": "high"}
    llm = core_engine.setup_llm(cfg, agent_cfg={"model_name": "m", "inference_params": {"reasoning_effort": "low"}})
    assert llm.extra_body["chat_template_kwargs"]["reasoning_effort"] == "low"


def test_stream_chunk_reasoning_content():
    llm = _make_llm()
    gen = llm._convert_chunk_to_generation_chunk(_chunk({"role": "assistant", "content": None, "reasoning_content": "Let me think"}), AIMessageChunk, {})
    assert gen.message.additional_kwargs["reasoning_content"] == "Let me think"


def test_stream_chunk_reasoning_alias():
    llm = _make_llm()
    gen = llm._convert_chunk_to_generation_chunk(_chunk({"content": "", "reasoning": "vllm style"}), AIMessageChunk, {})
    assert gen.message.additional_kwargs["reasoning_content"] == "vllm style"


def test_stream_chunk_no_duplicate_reasoning():
    llm = _make_llm()
    gen = llm._convert_chunk_to_generation_chunk(_chunk({"content": "", "reasoning_content": "abc"}), AIMessageChunk, {})
    reasoning, content = _extract_like_generation_thread(gen.message)
    assert reasoning == "abc"
    assert content == ""


def test_stream_chunk_plain_content_untouched():
    llm = _make_llm()
    gen = llm._convert_chunk_to_generation_chunk(_chunk({"content": "Hello"}), AIMessageChunk, {})
    assert "reasoning_content" not in gen.message.additional_kwargs
    reasoning, content = _extract_like_generation_thread(gen.message)
    assert reasoning == ""
    assert content == "Hello"


def test_non_stream_result_reasoning_content():
    llm = _make_llm()
    response = {
        "id": "x", "model": "test-model",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": "391", "reasoning_content": "17*23 = 391"}}],
        "usage": None,
    }
    result = llm._create_chat_result(response)
    msg = result.generations[0].message
    assert msg.content == "391"
    assert msg.additional_kwargs["reasoning_content"] == "17*23 = 391"
