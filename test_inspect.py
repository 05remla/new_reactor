import inspect
import toolz

def dummy_func():
    pass

toolz.dummy_func = dummy_func
funcs = inspect.getmembers(toolz, inspect.isfunction)
print([name for name, f in funcs if name == 'dummy_func'])
