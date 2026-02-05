from setuptools import setup, find_packages

setup(
    name="idea-bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flexus-client-kit",
        "requests",
        "openai",
        "anthropic",
    ],
    package_data={"": ["*.webp", "*.png", "*.html", "*.lark", "*.json"]},
)
