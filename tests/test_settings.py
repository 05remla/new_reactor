import pytest
import os
from settings import SettingsDialog
from PyQt5.QtWidgets import QMessageBox

def test_clear_checkpoint_db(qtbot, mocker, tmp_path):
    # Set up temporary directories to act as workspace
    da_root_dir = tmp_path / "workspace"
    da_root_dir.mkdir()
    
    # Create mock files one dir up from da_root_dir
    cp_file1 = tmp_path / "agent_checkpoints.db"
    cp_file2 = tmp_path / "agent_checkpoints.db-wal"
    cp_file3 = tmp_path / "agent_checkpoints.db-shm"
    other_file = tmp_path / "other.db"
    
    cp_file1.write_text("db content")
    cp_file2.write_text("wal content")
    cp_file3.write_text("shm content")
    other_file.write_text("other content")
    
    # Mock parent app and config
    mock_app = mocker.Mock()
    mock_app.config = {
        "da_root_dir": str(da_root_dir)
    }
    
    # Mock QMessageBox functions to automatically accept
    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes)
    mocker.patch.object(QMessageBox, 'information')
    mocker.patch.object(QMessageBox, 'critical')
    
    class TestSettingsDialog(SettingsDialog):
        def __init__(self, parent_app):
            super(SettingsDialog, self).__init__()
            self.app = parent_app
            self.config = parent_app.config
            self.ui = mocker.Mock()
            
    dialog = TestSettingsDialog(mock_app)
    
    # Call _clear_checkpoint_db
    dialog._clear_checkpoint_db()
    
    # Verify the matching files are deleted
    assert not cp_file1.exists()
    assert not cp_file2.exists()
    assert not cp_file3.exists()
    
    # Verify the non-matching file is not deleted
    assert other_file.exists()
    
    # Verify QMessageBox.question was called
    QMessageBox.question.assert_called_once()
    # Verify QMessageBox.information was called to show success
    QMessageBox.information.assert_called_with(dialog, "Success", "Successfully deleted 3 checkpoint file(s).")

def test_clear_checkpoint_db_no_files(qtbot, mocker, tmp_path):
    da_root_dir = tmp_path / "workspace"
    da_root_dir.mkdir()
    
    mock_app = mocker.Mock()
    mock_app.config = {
        "da_root_dir": str(da_root_dir)
    }
    
    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes)
    mocker.patch.object(QMessageBox, 'information')
    
    class TestSettingsDialog(SettingsDialog):
        def __init__(self, parent_app):
            super(SettingsDialog, self).__init__()
            self.app = parent_app
            self.config = parent_app.config
            self.ui = mocker.Mock()
            
    dialog = TestSettingsDialog(mock_app)
    dialog._clear_checkpoint_db()
    
    # Should show info about no files found
    QMessageBox.information.assert_called_with(dialog, "Clear Checkpoints", "No checkpoint files found to delete.")
    # Question dialog should not have been called
    QMessageBox.question.assert_not_called()

def test_clear_checkpoint_db_declined(qtbot, mocker, tmp_path):
    da_root_dir = tmp_path / "workspace"
    da_root_dir.mkdir()
    
    cp_file = tmp_path / "agent_checkpoints.db"
    cp_file.write_text("db content")
    
    mock_app = mocker.Mock()
    mock_app.config = {
        "da_root_dir": str(da_root_dir)
    }
    
    mocker.patch.object(QMessageBox, 'question', return_value=QMessageBox.No)
    mocker.patch.object(QMessageBox, 'information')
    
    class TestSettingsDialog(SettingsDialog):
        def __init__(self, parent_app):
            super(SettingsDialog, self).__init__()
            self.app = parent_app
            self.config = parent_app.config
            self.ui = mocker.Mock()
            
    dialog = TestSettingsDialog(mock_app)
    dialog._clear_checkpoint_db()
    
    # File should still exist
    assert cp_file.exists()
    QMessageBox.question.assert_called_once()
    QMessageBox.information.assert_not_called()
