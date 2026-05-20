"""chip-design-agent — 芯片研发管理自动化流水线"""

from setuptools import setup, find_packages

setup(
    name="chip-design-agent",
    version="1.0.0",
    description="芯片研发管理自动化流水线 Agent — 从规格书到 GDS",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "chip-pipeline=pipeline.cli:main",
        ],
    },
)
