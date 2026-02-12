from setuptools import setup, find_packages

setup(
    name="roastmaster",
    version="0.0.7",
    packages=find_packages(),
    install_requires=[
        "flexus-client-kit @ git+https://github.com/smallcloudai/flexus-client-kit.git",
        "requests",
        "openai",
        "anthropic",
    ],
    package_data={"": ["*.webp", "*.png", "*.html", "*.lark", "*.json"]},
)
