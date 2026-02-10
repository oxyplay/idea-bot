from setuptools import setup, find_packages

setup(
    name="roastmaster",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "flexus-client-kit @ git+https://github.com/smallcloudai/flexus-client-kit.git",
        "requests",
        "openai",
        "playwright",
        "anthropic",
        "pillow",
    ],
    package_data={"": ["*.webp", "*.png", "*.html", "*.lark", "*.json"]},
)
