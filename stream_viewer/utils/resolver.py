import importlib
import inspect
import os
import pathlib


def full_search_paths(sv_modulename, extra_search_dirs=[]):
    search_paths = []
    for search_dir in extra_search_dirs:
        search_paths.append(pathlib.Path(search_dir))
    search_paths.append(pathlib.Path(os.path.expanduser('~')) / '.stream_viewer' / 'plugins' / sv_modulename)
    search_paths[-1].mkdir(parents=True, exist_ok=True)
    search_paths.append(pathlib.Path(__file__).parents[1].absolute() / sv_modulename)
    return search_paths


def load_plugin_class(class_name, sv_modulename, extra_search_dirs=[]):
    """
    Search all .py files in all search directories and load the first class that matches
    `class_name`.
    The default search directories are extra_search_dirs (if provided),
    ~/.stream_viewer/plugins/sv_modulename, and the sv_modulename within stream_viewer itself.
    Additionally, if class_name has path separators, then the path up until the final
    separator is the first directory searched.

    Args:
        class_name: The name of the class to load. If providing a path, format as
        /path/to/folder/class_name -- do not include the containing .py filename.
        sv_modulename: The name of the stream_viewer module that will be searched.
        extra_search_dirs: A list of extra directories to search.

    Returns:
        The class object if found else None
    """
    search_paths = full_search_paths(sv_modulename, extra_search_dirs=extra_search_dirs)
    # If class_name is a full path, add its directory to the front of search_paths and replace class_name
    #  with the terminal class_name only.
    class_dir = os.path.dirname(class_name)
    if class_dir:
        class_name = os.path.split(class_name)[1]
        if os.path.isdir(class_dir):
            search_paths = [pathlib.Path(class_dir)] + search_paths
    for _path in search_paths:
        for entry in _path.iterdir():
            if not str(entry).endswith('.py'):
                continue
            module_path = entry.resolve()
            spec = importlib.util.spec_from_file_location(inspect.getmodulename(module_path), module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            objs = [obj for name, obj in inspect.getmembers(module, inspect.isclass)
                    if (class_name is None or name == class_name)]
            if len(objs) > 0:
                obj = objs[0]
                obj.__file__ = str(entry)
                return obj

    return None
