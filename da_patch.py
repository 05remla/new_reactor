import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def apply_deepagents_patches():
    """
    Applies runtime monkey-patches to the DeepAgents framework to fix path
    duplication issues when models hallucinate absolute paths.
    """
    try:
        from deepagents.backends.filesystem import FilesystemBackend
    except ImportError:
        # DeepAgents is not installed or available, skip patching
        return

    # Store the original method
    original_resolve_path = FilesystemBackend._resolve_path

    def patched_resolve_path(self, key: str) -> Path:
        if self.virtual_mode:
            # Handle absolute paths on the host filesystem that reside within the root directory.
            # This prevents deepagents from concatenating an already absolute path to the root_dir.
            path_obj = Path(key)
            if path_obj.is_absolute():
                resolved_path = path_obj.resolve()
                try:
                    # Check if it resides in the root_dir by attempting to get the relative path
                    resolved_path.relative_to(self.cwd)
                    return resolved_path
                except ValueError:
                    # If it escapes cwd, find the longest common parent and map the remainder inside cwd.
                    # This gracefully handles cases where the agent hallucinates the project root.
                    cwd_parts = self.cwd.parts
                    path_parts = resolved_path.parts
                    i = 0
                    while i < len(cwd_parts) and i < len(path_parts) and cwd_parts[i] == path_parts[i]:
                        i += 1
                    
                    if i < len(path_parts):
                        relative_remainder = Path(*path_parts[i:])
                        return (self.cwd / relative_remainder).resolve()
                    else:
                        return self.cwd
                
        # Call the original method for relative paths or non-virtual mode
        return original_resolve_path(self, key)

    # Apply the patch in memory
    FilesystemBackend._resolve_path = patched_resolve_path
    logger.info("DeepAgents filesystem path duplication monkey-patch applied successfully.")
