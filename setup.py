from setuptools import setup

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")
    print(install_requires)

setup(
    name='GST_Plugins_SmallObjDetection',
    version='v0.0.1',
    packages=['gst.python',],
    url='https://github.com/johnnewto/gst_plugins-small-object-detector',
    license='',
    author='john',
    author_email='',
    description='Small Object Detector plugin for Gstreamer.',
    install_requires=install_requires,
)
