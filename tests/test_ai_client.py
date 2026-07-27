import json
import pytest
from unittest.mock import patch, MagicMock
from backtranslate.ai.client import build_prompt, call_ai, parse_ai_response


def test_build_prompt():
    context = "Previous: 你好 -> Hello\nNext: 再见 -> Goodbye"
    user_input = "Hi"
    official = "Hello"
    template = "Context: {context}\nUser: {user_input}\nOfficial: {official}"
    result = build_prompt(template, context, user_input, official)
    assert "Previous:" in result
    assert "Hi" in result
    assert "Hello" in result


def test_parse_ai_response_valid_json():
    response = json.dumps({
        "meaning_score": 95,
        "grammar_score": 100,
        "naturalness_score": 82,
        "subtitle_style_score": 75,
        "analysis": "Good translation.",
        "suggested_expressions": ["well done"],
    })
    result = parse_ai_response(response)
    assert result["meaning_score"] == 95
    assert result["suggested_expressions"] == ["well done"]


def test_parse_ai_response_with_markdown_wrapper():
    response = '```json\n' + json.dumps({
        "meaning_score": 90, "grammar_score": 85,
        "naturalness_score": 80, "subtitle_style_score": 70,
        "analysis": "ok", "suggested_expressions": []
    }) + '\n```'
    result = parse_ai_response(response)
    assert result["meaning_score"] == 90


def test_parse_ai_response_invalid_json():
    result = parse_ai_response("not json at all")
    assert result is None


@patch("backtranslate.ai.client.requests.post")
def test_call_ai_success(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps({
            "meaning_score": 100, "grammar_score": 100,
            "naturalness_score": 100, "subtitle_style_score": 100,
            "analysis": "perfect", "suggested_expressions": []
        })}}]
    }
    mock_post.return_value = mock_response

    result = call_ai(
        "http://example.com/v1", "sk-test", "test-model",
        "You are a coach. Context: {context}\nUser: {user_input}\nOfficial: {official}",
        "Context text", "user input", "official text",
    )
    assert result is not None
    assert result["meaning_score"] == 100


@patch("backtranslate.ai.client.requests.post")
def test_call_ai_http_error(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    result = call_ai(
        "http://example.com/v1", "sk-test", "test-model",
        "prompt template {context} {user_input} {official}",
        "context", "user input", "official",
    )
    assert result is None
