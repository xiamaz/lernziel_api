import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="lernziel_api",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    author="Max Zhao",
    author_email="max.zhao@charite.de",
    description="Scrape lernzielplatform to get lernziele.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/xiamaz/lernziel_api",
    py_modules=["lernziel_api"],
    install_requires=[
        "requests",
        "lxml",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
