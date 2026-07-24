import os
import shutil
from PyQt5.QtWidgets import QMainWindow, QInputDialog, QMessageBox, QTreeWidgetItem, QAbstractItemView, QTreeWidget
from PyQt5.QtCore import Qt, QEvent
from workspace_manager_ui import Ui_MainWindow

WORKSPACES_DIR = "/home/leo/.pyvirtenvs/new_reactor/workspaces"

class WorkspaceManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Ensure workspaces dir exists
        os.makedirs(WORKSPACES_DIR, exist_ok=True)
        
        # Set multi-selection for destination tree just in case it's missing in UI
        self.ui.treeWidgetItemsDst.setSelectionMode(QAbstractItemView.MultiSelection)
        self.ui.treeWidgetItemsSrc.setSelectionMode(QAbstractItemView.MultiSelection)
        
        # Enable Drag and Drop
        for tree in (self.ui.treeWidgetItemsSrc, self.ui.treeWidgetItemsDst):
            tree.setDragEnabled(True)
            tree.setAcceptDrops(True)
            tree.setDropIndicatorShown(True)
            tree.setDragDropMode(QAbstractItemView.DragDrop)
            tree.viewport().installEventFilter(self)
            tree.installEventFilter(self)
            
            # Setup context menu
            tree.setContextMenuPolicy(Qt.CustomContextMenu)
            
        self.ui.treeWidgetItemsSrc.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(pos, self.ui.treeWidgetItemsSrc))
        self.ui.treeWidgetItemsDst.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(pos, self.ui.treeWidgetItemsDst))
        
        # Connect signals
        if hasattr(self.ui, 'pushButtonWorkspaceNew'):
            self.ui.pushButtonWorkspaceNew.clicked.connect(self.new_workspace)
        self.ui.comboBoxWorkspaceSrc.currentIndexChanged.connect(self.refresh_src_tree)
        self.ui.comboBoxWorkspaceDst.currentIndexChanged.connect(self.refresh_dst_tree)
        
        if hasattr(self.ui, 'pushButtonCopySrc2Dst'):
            self.ui.pushButtonCopySrc2Dst.clicked.connect(self.copy_src_to_dst)
        if hasattr(self.ui, 'pushButtonCopyDst2Src'):
            self.ui.pushButtonCopyDst2Src.clicked.connect(self.copy_dst_to_src)
        
        if hasattr(self.ui, 'pushButtonDeleteDst_2'):
            self.ui.pushButtonDeleteDst_2.clicked.connect(self.delete_src)
        if hasattr(self.ui, 'pushButtonDeleteDst'):
            self.ui.pushButtonDeleteDst.clicked.connect(self.delete_dst)
        
        if hasattr(self.ui, 'pushButtonClose'):
            self.ui.pushButtonClose.clicked.connect(self.close)
        
        self.refresh_comboboxes()

    def refresh_comboboxes(self):
        self.ui.comboBoxWorkspaceSrc.blockSignals(True)
        self.ui.comboBoxWorkspaceDst.blockSignals(True)
        
        src_current = self.ui.comboBoxWorkspaceSrc.currentText()
        dst_current = self.ui.comboBoxWorkspaceDst.currentText()
        
        self.ui.comboBoxWorkspaceSrc.clear()
        self.ui.comboBoxWorkspaceDst.clear()
        
        if os.path.exists(WORKSPACES_DIR):
            workspaces = [d for d in os.listdir(WORKSPACES_DIR) if os.path.isdir(os.path.join(WORKSPACES_DIR, d))]
            workspaces.sort()
            self.ui.comboBoxWorkspaceSrc.addItems(workspaces)
            self.ui.comboBoxWorkspaceDst.addItems(workspaces)
            
            # Restore previous selections if possible
            if src_current in workspaces:
                self.ui.comboBoxWorkspaceSrc.setCurrentText(src_current)
            if dst_current in workspaces:
                self.ui.comboBoxWorkspaceDst.setCurrentText(dst_current)
            
        self.ui.comboBoxWorkspaceSrc.blockSignals(False)
        self.ui.comboBoxWorkspaceDst.blockSignals(False)
        
        self.refresh_src_tree()
        self.refresh_dst_tree()

    def new_workspace(self):
        name, ok = QInputDialog.getText(self, "New Workspace", "Enter workspace name:")
        if ok and name.strip():
            name = name.strip()
            path = os.path.join(WORKSPACES_DIR, name)
            if not os.path.exists(path):
                os.makedirs(path)
                os.makedirs(os.path.join(path, "agent_space"), exist_ok=True)
                self.refresh_comboboxes()
                # Select the new workspace in destination by default
                index = self.ui.comboBoxWorkspaceDst.findText(name)
                if index >= 0:
                    self.ui.comboBoxWorkspaceDst.setCurrentIndex(index)
            else:
                QMessageBox.warning(self, "Error", "Workspace already exists!")

    def populate_tree(self, tree_widget, workspace_name):
        tree_widget.clear()
        if not workspace_name:
            return
            
        path = os.path.join(WORKSPACES_DIR, workspace_name)
        if not os.path.exists(path):
            return
            
        self._add_items_to_tree(tree_widget, path)
        tree_widget.expandAll()

    def _add_items_to_tree(self, parent, path):
        try:
            items = os.listdir(path)
        except PermissionError:
            return
            
        def sort_key(name):
            return (not os.path.isdir(os.path.join(path, name)), name.lower())
            
        for item_name in sorted(items, key=sort_key):
            item_path = os.path.join(path, item_name)
            is_dir = os.path.isdir(item_path)
            
            if isinstance(parent, QTreeWidgetItem):
                item = QTreeWidgetItem(parent)
            else:
                item = QTreeWidgetItem(parent)
                
            item.setText(0, "Directory" if is_dir else "File")
            item.setText(1, item_name)
            item.setData(0, Qt.UserRole, item_path)
            
            if is_dir:
                self._add_items_to_tree(item, item_path)

    def refresh_src_tree(self):
        self.populate_tree(self.ui.treeWidgetItemsSrc, self.ui.comboBoxWorkspaceSrc.currentText())

    def refresh_dst_tree(self):
        self.populate_tree(self.ui.treeWidgetItemsDst, self.ui.comboBoxWorkspaceDst.currentText())

    def get_selected_paths(self, tree_widget):
        paths = []
        for item in tree_widget.selectedItems():
            path = item.data(0, Qt.UserRole)
            if path:
                paths.append(path)
        
        # Filter out children whose parents are already selected
        paths = sorted(paths)
        filtered = []
        for p in paths:
            if not any(p.startswith(fp + os.sep) for fp in filtered):
                filtered.append(p)
        return filtered

    def copy_items(self, source_tree, dest_workspace_name, refresh_dest_func):
        if not dest_workspace_name:
            return
            
        dest_dir = os.path.join(WORKSPACES_DIR, dest_workspace_name)
        if not os.path.exists(dest_dir):
            return
            
        selected_paths = self.get_selected_paths(source_tree)
        if not selected_paths:
            return
            
        if source_tree == self.ui.treeWidgetItemsSrc:
            src_workspace_name = self.ui.comboBoxWorkspaceSrc.currentText()
        else:
            src_workspace_name = self.ui.comboBoxWorkspaceDst.currentText()
            
        src_workspace_dir = os.path.join(WORKSPACES_DIR, src_workspace_name)
        
        if src_workspace_dir == dest_dir:
            QMessageBox.warning(self, "Warning", "Source and destination workspaces are the same!")
            return
            
        for path in selected_paths:
            try:
                rel_path = os.path.relpath(path, src_workspace_dir)
                target_path = os.path.join(dest_dir, rel_path)
                
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                if os.path.isdir(path):
                    if os.path.exists(target_path):
                        shutil.rmtree(target_path)
                    shutil.copytree(path, target_path)
                else:
                    shutil.copy2(path, target_path)
            except Exception as e:
                print(f"Error copying {path} to {target_path}: {e}")
                
        refresh_dest_func()

    def copy_src_to_dst(self):
        self.copy_items(self.ui.treeWidgetItemsSrc, self.ui.comboBoxWorkspaceDst.currentText(), self.refresh_dst_tree)

    def copy_dst_to_src(self):
        self.copy_items(self.ui.treeWidgetItemsDst, self.ui.comboBoxWorkspaceSrc.currentText(), self.refresh_src_tree)

    def delete_items(self, tree_widget, refresh_func):
        selected_paths = self.get_selected_paths(tree_widget)
        if not selected_paths:
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Are you sure you want to delete {len(selected_paths)} item(s)?",
                                     QMessageBox.Yes | QMessageBox.No)
                                     
        if reply == QMessageBox.Yes:
            for path in selected_paths:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception as e:
                    print(f"Error deleting {path}: {e}")
            refresh_func()

    def delete_src(self):
        self.delete_items(self.ui.treeWidgetItemsSrc, self.refresh_src_tree)

    def delete_dst(self):
        self.delete_items(self.ui.treeWidgetItemsDst, self.refresh_dst_tree)

    def _show_context_menu(self, pos, tree_widget):
        from PyQt5.QtWidgets import QMenu
        if not tree_widget.selectedItems():
            return
            
        menu = QMenu(self)
        delete_action = menu.addAction("Delete Selected")
        
        action = menu.exec_(tree_widget.viewport().mapToGlobal(pos))
        
        if action == delete_action:
            if tree_widget == self.ui.treeWidgetItemsSrc:
                self.delete_src()
            else:
                self.delete_dst()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            tree = None
            if obj == self.ui.treeWidgetItemsSrc:
                tree = self.ui.treeWidgetItemsSrc
            elif obj == self.ui.treeWidgetItemsDst:
                tree = self.ui.treeWidgetItemsDst
                
            if tree:
                if event.key() == Qt.Key_Escape:
                    tree.clearSelection()
                    return True
                elif event.key() == Qt.Key_Delete:
                    if tree == self.ui.treeWidgetItemsSrc:
                        self.delete_src()
                    else:
                        self.delete_dst()
                    return True
                    
        if event.type() == QEvent.Drop:
            tree = None
            if obj == self.ui.treeWidgetItemsSrc.viewport():
                tree = self.ui.treeWidgetItemsSrc
            elif obj == self.ui.treeWidgetItemsDst.viewport():
                tree = self.ui.treeWidgetItemsDst
                
            if tree:
                source_tree = event.source()
                if isinstance(source_tree, QTreeWidget):
                    target_item = tree.itemAt(event.pos())
                    target_dir = None
                    
                    if target_item:
                        target_path = target_item.data(0, Qt.UserRole)
                        if os.path.isdir(target_path):
                            target_dir = target_path
                        else:
                            target_dir = os.path.dirname(target_path)
                    else:
                        workspace = self.ui.comboBoxWorkspaceSrc.currentText() if tree == self.ui.treeWidgetItemsSrc else self.ui.comboBoxWorkspaceDst.currentText()
                        if workspace:
                            target_dir = os.path.join(WORKSPACES_DIR, workspace)
                            
                    if target_dir and os.path.exists(target_dir):
                        selected_paths = self.get_selected_paths(source_tree)
                        for path in selected_paths:
                            if path == target_dir or path.startswith(target_dir + os.sep):
                                continue
                            
                            new_path = os.path.join(target_dir, os.path.basename(path))
                            try:
                                if os.path.isdir(path):
                                    if os.path.exists(new_path):
                                        shutil.rmtree(new_path)
                                    shutil.copytree(path, new_path)
                                else:
                                    shutil.copy2(path, new_path)
                            except Exception as e:
                                print(f"Drop error: {e}")
                                
                        self.refresh_src_tree()
                        self.refresh_dst_tree()
                        event.setDropAction(Qt.CopyAction)
                        event.accept()
                        return True
        return super().eventFilter(obj, event)

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = WorkspaceManager()
    window.show()
    sys.exit(app.exec_())
