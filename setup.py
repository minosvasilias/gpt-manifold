from setuptools import setup, find_packages
from setuptools import setup

setup(
    name="gpt_manifold",
    version="1.0.2",
    packages=find_packages(),
    install_requires=[
        "openai",
        "pick"
    ],
    author="Markus Sobkowski",
    author_email="sobmarski@gmail.com",
    description="An assistant for betting on prediction markets on manifold.markets, utilizing OpenAI's GPT APIs.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/minosvasilias/gpt-manifold",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
