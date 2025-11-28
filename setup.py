from setuptools import setup, find_packages

setup(
    name="log-analyzer",
    version="0.1.0",
    description="AI-powered log analysis tool using Ollama",
    author="Your Name",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.1.0",
        "requests>=2.31.0",
        "pyyaml>=6.0",
        "pandas>=2.0.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "log-analyzer=cli.main:main",
        ],
    },
    python_requires=">=3.8",
)
