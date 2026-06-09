import inspect
import toolz
import memory_redux_plugin
toolz.manage_memory = memory_redux_plugin.manage_memory
funcs = inspect.getmembers(toolz, inspect.isfunction)
print([name for name, f in funcs if name == 'manage_memory'])
