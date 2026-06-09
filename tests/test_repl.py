import pytest
from repl import ReplApp
from config_manager import ConfigManager
import os

def test_repl_app_initialization(mocker, tmp_path):
    # Mock config
    config_file = tmp_path / "config.json"
    config_file.write_text("{}")
    cm = ConfigManager(str(config_file))
    
    app = ReplApp(config_manager=cm)
    assert app is not None
    assert app.prompt == ""
    assert app.history == []
