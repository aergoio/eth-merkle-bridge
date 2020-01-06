import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="eth-merkle-bridge",
    version="0.3.4",
    author="Pierre-Alain Ouvrard",
    author_email="ouvrard.pierre.alain@gmail.com",
    description="POC implementation of the eth-merkle-bridge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aergoio/eth-merkle-bridge",
    packages=setuptools.find_packages(),
    install_requires=[
        "aergo-herapy==2.0.0",
        "web3==5.4.0",
        "merkle-bridge @ git+git://github.com/aergoio/merkle-bridge.git@v0.3.0#egg=merkle-bridge",
        "trie==1.4.0",
        "PyInquirer",
        "pyfiglet"
    ],
    classifiers=[
                "Programming Language :: Python :: 3.7",
                "License :: OSI Approved :: MIT License",
                "Operating System :: OS Independent",
            ],
)
