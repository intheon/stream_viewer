import setuptools
import os


# Get the long description from the relevant file
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'docs', 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the version number from the version file
# Versions should comply with PEP440.  For a discussion on single-sourcing
# the version across setup.py and the project code, see
# https://packaging.python.org/en/latest/single_source_version.html
version = {}
with open("stream_viewer/version.py") as fp:
    exec(fp.read(), version)


setuptools.setup(
    name='stream_viewer',
    version=version['__version__'],
    description='Tools to visualize data streamed with Lab Streaming Layer',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/intheon/stream_viewer',
    author='Chadwick Boulay',
    author_email='chadwick.boulay@gmail.com',
    license='MIT',
    packages=setuptools.find_packages(),
    package_data={
        'stream_viewer': ['qml/streamInfoListView.qml'],
    },
    install_requires=['qtpy', 'pandas', 'pylsl', 'vispy', 'pyqtgraph', 'matplotlib', 'scipy'],
    extras_require={'PYQT': ["pyqt5"], 'PYSIDE': ["PySide6"]},
    entry_points={'gui_scripts': ['lsl_viewer=stream_viewer.applications.main:main',
                                  'lsl_status=stream_viewer.applications.stream_status_qml:main',
                                  'lsl_switching_viewer=stream_viewer.applications.lsl_switching:main'],
                  'console_scripts': ['lsl_viewer_custom=stream_viewer.applications.lsl_custom:main']}
)
