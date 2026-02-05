from setuptools import setup, find_packages

setup(
    name="flexus-bots",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flexus-client-kit",
        "requests",
        "openai",
        "anthropic",
        "pillow",
        "playwright",
    ],
    package_data={"": ["*.webp", "*.png", "*.html", "*.lark", "*.json"]},
)
