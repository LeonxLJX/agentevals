"""Centralized OTel span attribute key constants.

Single source of truth for all attribute names used across the converter,
extraction, streaming, and runner modules.

Covers OTel GenAI semantic conventions up to v1.40.0.
"""

# OTel resource
OTEL_SERVICE_NAME = "service.name"

# OTel scope
OTEL_SCOPE = "otel.scope.name"
OTEL_SCOPE_VERSION = "otel.scope.version"

# Google ADK scope value
ADK_SCOPE_VALUE = "gcp.vertex.agent"

# Standard OTel GenAI semantic conventions (gen_ai.*)
OTEL_GENAI_OP = "gen_ai.operation.name"
OTEL_GENAI_AGENT_NAME = "gen_ai.agent.name"
OTEL_GENAI_REQUEST_MODEL = "gen_ai.request.model"
OTEL_GENAI_INPUT_MESSAGES = "gen_ai.input.messages"
OTEL_GENAI_OUTPUT_MESSAGES = "gen_ai.output.messages"
OTEL_GENAI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
OTEL_GENAI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
OTEL_GENAI_TOOL_NAME = "gen_ai.tool.name"
OTEL_GENAI_TOOL_CALL_ID = "gen_ai.tool.call.id"
OTEL_GENAI_TOOL_CALL_ARGUMENTS = "gen_ai.tool.call.arguments"
OTEL_GENAI_TOOL_CALL_RESULT = "gen_ai.tool.call.result"
OTEL_GENAI_CONVERSATION_ID = "gen_ai.conversation.id"

# Provider and response metadata (v1.37.0+)
OTEL_GENAI_PROVIDER_NAME = "gen_ai.provider.name"
OTEL_GENAI_RESPONSE_MODEL = "gen_ai.response.model"
OTEL_GENAI_RESPONSE_ID = "gen_ai.response.id"
OTEL_GENAI_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"

# Deprecated provider attribute (pre-v1.37.0, renamed to gen_ai.provider.name)
OTEL_GENAI_SYSTEM = "gen_ai.system"

# Agent identity (v1.31.0+)
OTEL_GENAI_AGENT_ID = "gen_ai.agent.id"
OTEL_GENAI_AGENT_DESCRIPTION = "gen_ai.agent.description"

# Tool metadata (v1.31.0+)
OTEL_GENAI_TOOL_DESCRIPTION = "gen_ai.tool.description"
OTEL_GENAI_TOOL_TYPE = "gen_ai.tool.type"

# Error classification
OTEL_ERROR_TYPE = "error.type"

# Request parameters
OTEL_GENAI_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
OTEL_GENAI_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
OTEL_GENAI_REQUEST_TOP_P = "gen_ai.request.top_p"
OTEL_GENAI_REQUEST_TOP_K = "gen_ai.request.top_k"

# Cache token usage (Anthropic/OpenAI prompt caching)
OTEL_GENAI_USAGE_CACHE_CREATION_TOKENS = "gen_ai.usage.cache_creation.input_tokens"
OTEL_GENAI_USAGE_CACHE_READ_TOKENS = "gen_ai.usage.cache_read.input_tokens"

# System/tool definitions (opt-in, v1.37.0+)
OTEL_GENAI_SYSTEM_INSTRUCTIONS = "gen_ai.system_instructions"
OTEL_GENAI_TOOL_DEFINITIONS = "gen_ai.tool.definitions"

# Output type
OTEL_GENAI_OUTPUT_TYPE = "gen_ai.output.type"

# ADK-specific custom attributes (gcp.vertex.agent.*)
ADK_LLM_REQUEST = "gcp.vertex.agent.llm_request"
ADK_LLM_RESPONSE = "gcp.vertex.agent.llm_response"
ADK_TOOL_CALL_ARGS = "gcp.vertex.agent.tool_call_args"
ADK_TOOL_RESPONSE = "gcp.vertex.agent.tool_response"
ADK_INVOCATION_ID = "gcp.vertex.agent.invocation_id"
