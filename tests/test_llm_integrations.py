import pytest
from unittest.mock import patch, MagicMock

def test_gemini_integration(mocker):
    # Mocking ChatGoogleGenerativeAI to prevent real API calls
    mock_llm_class = mocker.patch("langchain_google_genai.ChatGoogleGenerativeAI")
    mock_instance = mock_llm_class.return_value
    mock_instance.invoke.return_value = MagicMock(content="Mocked Gemini response")

    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key="fake", include_thoughts=True)
    res = llm.invoke("Hello")
    assert res.content == "Mocked Gemini response"

def test_openai_integration(mocker):
    mock_openai = mocker.patch("openai.OpenAI")
    mock_client = mock_openai.return_value
    mock_client.models.list.return_value = {"data": [{"id": "gpt-4"}]}

    from openai import OpenAI
    client = OpenAI(base_url="http://fake:8081/v1", api_key="fake-key", max_retries=0)
    res = client.models.list()
    assert res["data"][0]["id"] == "gpt-4"
