from stream_viewer.utils import load_plugin_class


def load_widget(widget_name, extra_search_dirs=[]):
    return load_plugin_class(widget_name, 'widgets', extra_search_dirs=extra_search_dirs)
