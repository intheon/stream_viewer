from stream_viewer.utils import load_plugin_class


def load_widget(widget_name):
    return load_plugin_class(widget_name, 'widgets')
