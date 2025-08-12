from setuptools import setup, find_packages

setup(
    name="EchoMux",
    version="1.0.0",
    description="Multi-Track Video Remuxer & Media Manager",
    author="Mohammed Al-hassan",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.0.0",
        "psutil>=5.8.0",
    ],
    entry_points={
        'console_scripts': [
            'echomux=echomux:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['icons/*'],
    },
)