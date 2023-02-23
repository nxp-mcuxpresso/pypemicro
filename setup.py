from setuptools import setup, find_packages

with open("README.md") as readme_file:
    README = readme_file.read()

with open("HISTORY.md") as history_file:
    HISTORY = history_file.read()

setup_args = dict(
    name="pypemicro",
    version="0.1.11",
    description="Python tool to control PEMicro Debug probes",
    long_description_content_type="text/markdown",
    long_description=README + "\n\n" + HISTORY,
    platforms="Windows, Linux, Mac OSX",
    python_requires=">=3.7",
    setup_requires=["setuptools>=40.0"],
    license="BSD-3-Clause",
    packages=find_packages(),
    author="Petr Gargulak",
    author_email="petr.gargulak@nxp.com",
    keywords=["PEMicro", "PyPEMicro"],
    url="https://github.com/nxpmicro/pypemicro",
    download_url="https://pypi.org/project/pypemicro/",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "License :: OSI Approved :: BSD License",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Embedded Systems",
        "Topic :: System :: Hardware",
        "Topic :: Utilities",
    ],
)

setup(**setup_args)
