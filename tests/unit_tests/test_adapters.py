"""Unit tests for adapter classes in sre_agent/llm/utils/adapters.py."""

# ruff: noqa: E402

import os
import sys
from unittest import TestCase

from anthropic.types import TextBlock as AnthropicTextBlock
from anthropic.types import ToolUseBlock as AnthropicToolUseBlock
from google.genai.types import Candidate as GeminiCandidate
from google.genai.types import Content as GeminiContent
from google.genai.types import FunctionCall as GeminiFunctionCall
from google.genai.types import Part as GeminiPart
from mcp.types import Tool

sys.path.insert(0, os.path.abspath("sre_agent"))

from shared.schemas import (
    MessageBlock,
    TextBlock,
    TextGenerationPayload,
    ToolResultBlock,
    ToolUseBlock,
)

from sre_agent.llm.utils.adapters import (
    AnthropicTextGenerationPayloadAdapter,
    AnthropicToMCPAdapter,
    GeminiTextGenerationPayloadAdapter,
    GeminiToMCPAdapter,
)


class TestAnthropicToMCPAdapter(TestCase):
    """Test cases for AnthropicToMCPAdapter."""

    def test_adapt_text_block(self):
        """Test adapting Anthropic text block to MCP text block."""
        anthropic_text = AnthropicTextBlock(type="text", text="Hello, world!")
        adapter = AnthropicToMCPAdapter([anthropic_text])

        result = adapter.adapt()

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextBlock)
        self.assertEqual(result[0].text, "Hello, world!")
        self.assertEqual(result[0].type, "text")

    def test_adapt_tool_use_block(self):
        """Test adapting Anthropic tool use block to MCP tool use block."""
        anthropic_tool_use = AnthropicToolUseBlock(
            id="test-id", name="test-tool", input={"param": "value"}, type="tool_use"
        )
        adapter = AnthropicToMCPAdapter([anthropic_tool_use])

        result = adapter.adapt()

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ToolUseBlock)
        self.assertEqual(result[0].id, "test-id")
        self.assertEqual(result[0].name, "test-tool")
        self.assertEqual(result[0].arguments, {"param": "value"})
        self.assertEqual(result[0].type, "tool_use")

    def test_adapt_mixed_content(self):
        """Test adapting mixed content types."""
        anthropic_text = AnthropicTextBlock(type="text", text="Hello")
        anthropic_tool_use = AnthropicToolUseBlock(
            id="tool-id", name="my-tool", input={"arg": "test"}, type="tool_use"
        )
        adapter = AnthropicToMCPAdapter([anthropic_text, anthropic_tool_use])

        result = adapter.adapt()

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], TextBlock)
        self.assertEqual(result[0].text, "Hello")
        self.assertIsInstance(result[1], ToolUseBlock)
        self.assertEqual(result[1].id, "tool-id")

    def test_adapt_unsupported_content_type(self):
        """Test that unsupported content type raises TypeError."""
        unsupported_content = {"type": "unsupported", "keys": lambda: ["type"]}
        adapter = AnthropicToMCPAdapter([unsupported_content])

        with self.assertRaises(TypeError) as context:
            adapter.adapt()
        self.assertIn("Unsupported content type", str(context.exception))


class TestAnthropicTextGenerationPayloadAdapter(TestCase):
    """Test cases for AnthropicTextGenerationPayloadAdapter."""

    def test_adapt_messages_with_text_block(self):
        """Test adapting messages containing text blocks."""
        payload = TextGenerationPayload(
            messages=[MessageBlock(role="user", content=[TextBlock(text="Hello")])],
            tools=[],
        )
        adapter = AnthropicTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(len(messages[0]["content"]), 1)
        self.assertEqual(messages[0]["content"][0].text, "Hello")
        self.assertEqual(messages[0]["content"][0].type, "text")

    def test_adapt_messages_with_tool_use_block(self):
        """Test adapting messages containing tool use blocks."""
        payload = TextGenerationPayload(
            messages=[
                MessageBlock(
                    role="assistant",
                    content=[
                        ToolUseBlock(
                            id="test-id", name="test-tool", arguments={"param": "value"}
                        )
                    ],
                )
            ],
            tools=[],
        )
        adapter = AnthropicTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "assistant")
        self.assertEqual(len(messages[0]["content"]), 1)
        tool_use = messages[0]["content"][0]
        self.assertEqual(tool_use.id, "test-id")
        self.assertEqual(tool_use.name, "test-tool")
        self.assertEqual(tool_use.input, {"param": "value"})
        self.assertEqual(tool_use.type, "tool_use")

    def test_adapt_messages_with_tool_result_block(self):
        """Test adapting messages containing tool result blocks."""
        payload = TextGenerationPayload(
            messages=[
                MessageBlock(
                    role="user",
                    content=[
                        ToolResultBlock(
                            tool_use_id="test-id",
                            name="Tool name (dummy)",
                            content="Tool result",
                            is_error=False,
                            type="tool_result",
                        )
                    ],
                )
            ],
            tools=[],
        )
        adapter = AnthropicTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(len(messages[0]["content"]), 1)
        tool_result = messages[0]["content"][0]
        self.assertEqual(tool_result["tool_use_id"], "test-id")
        self.assertEqual(tool_result["content"], "Tool result")
        self.assertFalse(tool_result["is_error"])
        self.assertEqual(tool_result["type"], "tool_result")

    def test_adapt_messages_with_mixed_content(self):
        """Test adapting messages with mixed content types."""
        payload = TextGenerationPayload(
            messages=[
                MessageBlock(
                    role="assistant",
                    content=[
                        TextBlock(text="Here's the result:"),
                        ToolUseBlock(
                            id="tool-id",
                            name="calculator",
                            arguments={"operation": "add", "a": 1, "b": 2},
                        ),
                    ],
                )
            ],
            tools=[],
        )
        adapter = AnthropicTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(messages), 1)
        self.assertEqual(len(messages[0]["content"]), 2)
        self.assertEqual(messages[0]["content"][0].text, "Here's the result:")
        self.assertEqual(messages[0]["content"][1].name, "calculator")

    def test_adapt_tools(self):
        """Test adapting tools from MCP to Anthropic format."""
        tools = [
            Tool(
                name="test-tool",
                description="A test tool",
                inputSchema={
                    "type": "object",
                    "properties": {"param": {"type": "string"}},
                },
            )
        ]
        payload = TextGenerationPayload(messages=[], tools=tools)
        adapter = AnthropicTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "test-tool")
        self.assertEqual(tools[0]["description"], "A test tool")
        self.assertEqual(
            tools[0]["input_schema"],
            {"type": "object", "properties": {"param": {"type": "string"}}},
        )

    def test_adapt_tools_without_description(self):
        """Test adapting tools that have no description."""
        tools = [Tool(name="test-tool", inputSchema={"type": "object"})]
        payload = TextGenerationPayload(messages=[], tools=tools)
        adapter = AnthropicTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "test-tool")
        self.assertEqual(tools[0]["description"], "")
        self.assertEqual(tools[0]["input_schema"], {"type": "object"})


class TestGeminiToMCPAdapter(TestCase):
    """Test cases for GeminiToMCPAdapter."""

    def test_adapt_text_block(self):
        """Test adapting Gemini text block to MCP text block."""
        gemini_part = GeminiPart(text="Hello, world!")
        gemini_content = GeminiContent(parts=[gemini_part], role="user")
        gemini_candidate = GeminiCandidate(content=gemini_content)
        adapter = GeminiToMCPAdapter([gemini_candidate])

        result = adapter.adapt()

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], TextBlock)
        self.assertEqual(result[0].text, "Hello, world!")
        self.assertEqual(result[0].type, "text")

    def test_adapt_tool_use_block(self):
        """Test adapting Gemini function call to MCP tool use block."""
        function_call = GeminiFunctionCall(
            id="test-id", name="test-tool", args={"param": "value"}
        )
        gemini_part = GeminiPart(function_call=function_call)
        gemini_content = GeminiContent(parts=[gemini_part], role="model")
        gemini_candidate = GeminiCandidate(content=gemini_content)
        adapter = GeminiToMCPAdapter([gemini_candidate])

        result = adapter.adapt()

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ToolUseBlock)
        self.assertEqual(result[0].id, "test-id")
        self.assertEqual(result[0].name, "test-tool")
        self.assertEqual(result[0].arguments, {"param": "value"})
        self.assertEqual(result[0].type, "tool_use")

    def test_adapt_mixed_content(self):
        """Test adapting mixed content types."""
        text_part = GeminiPart(text="Hello")
        function_call = GeminiFunctionCall(name="my-tool", args={"arg": "test"})
        function_part = GeminiPart(function_call=function_call)
        gemini_content = GeminiContent(parts=[text_part, function_part], role="model")
        gemini_candidate = GeminiCandidate(content=gemini_content)
        adapter = GeminiToMCPAdapter([gemini_candidate])

        result = adapter.adapt()

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], TextBlock)
        self.assertEqual(result[0].text, "Hello")
        self.assertIsInstance(result[1], ToolUseBlock)
        self.assertEqual(result[1].name, "my-tool")

    def test_adapt_unsupported_content_type(self):
        """Test that unsupported content type raises TypeError."""
        unsupported_part = GeminiPart()
        gemini_content = GeminiContent(parts=[unsupported_part], role="model")
        gemini_candidate = GeminiCandidate(content=gemini_content)
        adapter = GeminiToMCPAdapter([gemini_candidate])

        with self.assertRaises(TypeError) as context:
            adapter.adapt()
        self.assertIn("Unsupported part type", str(context.exception))


class TestGeminiTextGenerationPayloadAdapter(TestCase):
    """Test cases for GeminiTextGenerationPayloadAdapter."""

    def test_adapt_messages_with_text_block(self):
        """Test adapting messages containing text blocks."""
        payload = TextGenerationPayload(
            messages=[MessageBlock(role="user", content=[TextBlock(text="Hello")])],
            tools=[],
        )
        adapter = GeminiTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(len(messages[0].parts), 1)
        self.assertEqual(messages[0].parts[0].text, "Hello")

    def test_adapt_messages_with_tool_use_block(self):
        """Test adapting messages containing tool use blocks."""
        payload = TextGenerationPayload(
            messages=[
                MessageBlock(
                    role="assistant",
                    content=[
                        ToolUseBlock(
                            id="test-id", name="test-tool", arguments={"param": "value"}
                        )
                    ],
                )
            ],
            tools=[],
        )
        adapter = GeminiTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].role, "assistant")
        self.assertEqual(len(messages[0].parts), 1)
        function_call = messages[0].parts[0].function_call
        self.assertEqual(function_call.name, "test-tool")
        self.assertEqual(function_call.args, {"param": "value"})

    def test_adapt_messages_with_tool_result_block(self):
        """Test adapting messages containing tool result blocks."""
        payload = TextGenerationPayload(
            messages=[
                MessageBlock(
                    role="user",
                    content=[
                        ToolResultBlock(
                            tool_use_id="test-id",
                            name="Tool name",
                            content="Tool result",
                            is_error=False,
                            type="tool_result",
                        )
                    ],
                )
            ],
            tools=[],
        )
        adapter = GeminiTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].role, "user")
        self.assertEqual(len(messages[0].parts), 1)
        function_response = messages[0].parts[0].function_response
        self.assertEqual(function_response.name, "Tool name")
        self.assertEqual(function_response.response["output"], "Tool result")
        self.assertFalse(function_response.response["error"])

    def test_adapt_messages_with_mixed_content(self):
        """Test adapting messages with mixed content types."""
        payload = TextGenerationPayload(
            messages=[
                MessageBlock(
                    role="assistant",
                    content=[
                        TextBlock(text="Here's the result:"),
                        ToolUseBlock(
                            id="tool-id",
                            name="calculator",
                            arguments={"operation": "add", "a": 1, "b": 2},
                        ),
                    ],
                )
            ],
            tools=[],
        )
        adapter = GeminiTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(messages), 1)
        self.assertEqual(len(messages[0].parts), 2)
        self.assertEqual(messages[0].parts[0].text, "Here's the result:")
        self.assertEqual(messages[0].parts[1].function_call.name, "calculator")

    def test_adapt_tools(self):
        """Test adapting tools from MCP to Gemini format."""
        tools = [
            Tool(
                name="test-tool",
                description="A test tool",
                inputSchema={
                    "type": "object",
                    "properties": {"param": {"type": "string"}},
                },
            )
        ]
        payload = TextGenerationPayload(messages=[], tools=tools)
        adapter = GeminiTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(tools), 1)
        self.assertEqual(len(tools[0].function_declarations), 1)
        function_decl = tools[0].function_declarations[0]
        self.assertEqual(function_decl.name, "test-tool")
        self.assertEqual(function_decl.description, "A test tool")
        self.assertEqual(function_decl.parameters.type.value, "OBJECT")
        self.assertEqual(
            function_decl.parameters.properties["param"].type.value, "STRING"
        )

    def test_adapt_tools_without_description(self):
        """Test adapting tools that have no description."""
        tools = [Tool(name="test-tool", inputSchema={"type": "object"})]
        payload = TextGenerationPayload(messages=[], tools=tools)
        adapter = GeminiTextGenerationPayloadAdapter(payload)

        messages, tools = adapter.adapt()

        self.assertEqual(len(tools), 1)
        self.assertEqual(len(tools[0].function_declarations), 1)
        function_decl = tools[0].function_declarations[0]
        self.assertEqual(function_decl.name, "test-tool")
        self.assertIsNone(function_decl.description)
        self.assertEqual(function_decl.parameters.type.value, "OBJECT")
