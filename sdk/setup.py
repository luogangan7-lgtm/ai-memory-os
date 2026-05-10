from setuptools import setup, find_packages
setup(
    name="memory-os-sdk", version="0.1.0",
    packages=find_packages(),
    install_requires=["httpx>=0.27"],
    python_requires=">=3.10",
    description="AI Memory OS Agent SDK",
    author="Memory OS Team",
)
