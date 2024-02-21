from pathlib import Path
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="translator_deepl",
    description="Traslate a .SRT file using any custom translator",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/nguyentthai96/SRTranslator",
    version="0.2.11",
    author="Nguyen Thanh Thai",
    author_email="nguyentthai96@gmail.com",
    license="FREE",
    python_requires=">=3.6",
    install_requires=requirements,
    packages=find_packages(),
    keywords=["python", "srt", "languages", "translator", "subtitles"],
)
