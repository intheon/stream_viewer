from stream_viewer.utils import load_plugin_class


def load_buffer(buffer_name):
    return load_plugin_class(buffer_name, 'buffers')
