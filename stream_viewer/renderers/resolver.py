import importlib
import inspect
from stream_viewer.utils import load_plugin_class, full_search_paths
from stream_viewer.renderers.data.base import RendererFormatData
from stream_viewer.renderers.display.base import RendererBaseDisplay


def load_renderer(renderer_name: str, extra_search_dirs=[]):
    """
    Get the obj of the renderer class given the name of the renderer.
    See `list_renderers` to get a list of available renderers.
    Args:
        renderer_name: The name of the renderer to load.
        extra_search_dirs: a list of strings or Paths to search in addition to the defaults.
    Returns:
        The obj of the renderer class, or None

    """
    return load_plugin_class(renderer_name, 'renderers', extra_search_dirs=extra_search_dirs)


def list_renderers(extra_search_dirs=[], interface_classes=[RendererFormatData, RendererBaseDisplay]):
    """
    What renderers are available? Finds the name of renderers in the stream_viewer.renderers module,
    the user/.stream_viewer/plugins/renderers folder, and any other directories in
    extra_search_dirs.

    Args:
        extra_search_dirs: a list of strings or Paths to search in addition to the defaults.
    Returns: a list of found renderer names.
    """
    search_paths = full_search_paths('renderers', extra_search_dirs=extra_search_dirs)

    found_renderers = set()
    for _path in search_paths:
        for entry in _path.iterdir():
            if not str(entry).endswith('.py'):
                continue
            module_path = entry.resolve()
            spec = importlib.util.spec_from_file_location(inspect.getmodulename(module_path), module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if all([issubclass(obj, _) for _ in interface_classes]):
                    found_renderers.add(name)
    return list(found_renderers)


def get_kwargs_from_settings(settings, rend_cls):
    rend_kwargs = {}
    for rend_key in settings.allKeys():
        if rend_key.startswith('data_sources') or rend_key.lower().startswith('renderer'):
            continue
        if rend_key in rend_cls.gui_kwargs:
            val = settings.value(rend_key, type=rend_cls.gui_kwargs[rend_key])
        else:
            val = settings.value(rend_key)
            if val == 'true':
                val = True
            elif val == 'false':
                val = False
            # TODO: Further coerce strings to appropriate types.
        rend_kwargs[rend_key] = val
    return rend_kwargs
