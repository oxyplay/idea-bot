from setuptools import setup, find_packages

setup(
    name="idea_bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flexus-client-kit @ git+https://github.com/smallcloudai/flexus-client-kit.git",
        "requests",
        "openai",
        "anthropic",
        "pillow",
    ],
    package_data={"": ["*.webp", "*.png", "*.html", "*.lark", "*.json"]},
)
