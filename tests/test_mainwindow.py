import pytest
from PyQt5.QtCore import Qt
from mainwindow import MstyCloneApp
import requests

def test_mainwindow_initialization(qtbot, mocker):
    # Mock requests.get to prevent network calls during initialization
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"data": []}
    mock_response.status_code = 200
    mocker.patch('requests.get', return_value=mock_response)

    # Initialize the main app
    app = MstyCloneApp(config_filename="config.json")
    qtbot.addWidget(app)

    # Validate that it loaded properly
    assert app is not None
    assert app.is_loading is False
    
    # Test that the config was loaded
    assert app.config is not None
