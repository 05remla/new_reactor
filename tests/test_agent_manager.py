import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QListWidget, QListWidgetItem
from agent_manager import AgentManagerDialog

def test_load_agent_updates_label_model_tab_provider(qtbot, mocker, tmp_path):
    mock_app = mocker.Mock()
    mock_app.config_file = str(tmp_path / "config.json")
    mock_app.config = {
        "saved_provider_urls": ["http://localhost:11434/v1", "http://localhost:8081/v1"],
        "default_chat_agent": "TestAgent"
    }
    
    agent_configs = {
        "AgentA": {"model_name": "model-a", "provider_url": "http://localhost:11434/v1"},
        "AgentB": {"model_name": "model-b", "provider_url": "http://localhost:8081/v1"},
    }
    
    mock_cfg_mgr = mocker.Mock()
    mock_cfg_mgr.list_agents.return_value = ["AgentA", "AgentB"]
    mock_cfg_mgr.get_agent_config.side_effect = lambda name: dict(agent_configs.get(name, {}))
    mock_cfg_mgr.get_agents_dir.return_value = str(tmp_path / "agents")
    mock_app.config_manager = mock_cfg_mgr

    mocker.patch("theme_manager.apply_theme")

    dialog = AgentManagerDialog(mock_app)
    qtbot.addWidget(dialog)

    # Initial load of default or first agent
    dialog._load_agent_config("AgentA")
    assert dialog.ui.labelModelTabProvider.text() == "http://localhost:11434/v1"

    # Switching agent updates labelModelTabProvider
    dialog.ui.agent_combo.setCurrentText("AgentB")
    assert dialog.ui.labelModelTabProvider.text() == "http://localhost:8081/v1"

def test_provider_selection_updates_label_model_tab_provider(qtbot, mocker, tmp_path):
    mock_app = mocker.Mock()
    mock_app.config_file = str(tmp_path / "config.json")
    mock_app.config = {
        "saved_provider_urls": ["http://localhost:11434/v1", "http://localhost:8081/v1"],
        "default_chat_agent": "AgentA"
    }
    
    agent_configs = {
        "AgentA": {"model_name": "model-a", "provider_url": "http://localhost:11434/v1"}
    }
    
    mock_cfg_mgr = mocker.Mock()
    mock_cfg_mgr.list_agents.return_value = ["AgentA"]
    mock_cfg_mgr.get_agent_config.side_effect = lambda name: agent_configs.setdefault(name, {})
    mock_cfg_mgr.save_agent_config = mocker.Mock()
    mock_cfg_mgr.get_agents_dir.return_value = str(tmp_path / "agents")
    mock_app.config_manager = mock_cfg_mgr

    mocker.patch("theme_manager.apply_theme")

    dialog = AgentManagerDialog(mock_app)
    qtbot.addWidget(dialog)

    dialog._load_agent_config("AgentA")
    assert dialog.ui.labelModelTabProvider.text() == "http://localhost:11434/v1"

    # Select another provider in the list widget
    items = dialog.ui.listWidgetProviders.findItems("http://localhost:8081/v1", Qt.MatchExactly)
    if not items:
        dialog.ui.listWidgetProviders.addItem("http://localhost:8081/v1")
        item = dialog.ui.listWidgetProviders.item(dialog.ui.listWidgetProviders.count() - 1)
    else:
        item = items[0]

    dialog.ui.listWidgetProviders.setCurrentItem(item)
    dialog._on_provider_selected(item)
    assert dialog.ui.labelModelTabProvider.text() == "http://localhost:8081/v1"
