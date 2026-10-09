import pytest
from streamlit.testing.v1 import AppTest

from client import AgentClient


@pytest.mark.docker
def test_service_with_fake_model():
    """Test the service using the fake model.

    This test requires the service container to be running with USE_FAKE_MODEL=true
    """
    client = AgentClient("http://0.0.0.0", agent="campus-customer-service")
    response = client.invoke("你好，请介绍一下这个校园客服演示。", model="fake")
    assert response.type == "ai"
    assert response.content == "This is a test response from the fake model."


@pytest.mark.docker
def test_service_with_app():
    """Test the service using the app.

    This test requires the service container to be running with USE_FAKE_MODEL=true
    """
    at = AppTest.from_file("../../src/streamlit_app.py").run()
    assert at.chat_message[0].avatar == "🎓"
    welcome = at.chat_message[0].markdown[0].value
    assert welcome.startswith("你好！")
    assert not at.exception

    at.sidebar.selectbox[1].set_value("SIM-USER-001")
    at.chat_input[0].set_value("你好，请介绍一下这个校园客服演示。").run()
    assert at.chat_message[0].avatar == "user"
    assert at.chat_message[0].markdown[0].value == "你好，请介绍一下这个校园客服演示。"
    assert at.chat_message[1].avatar == "🎓"
    assert at.chat_message[1].markdown[0].value == "This is a test response from the fake model."
    assert not at.exception
