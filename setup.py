import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="eth-merkle-bridge",
    version="0.0.2",
    author="Pierre-Alain Ouvrard",
    author_email="ouvrard.pierre.alain@gmail.com",
    description="POC implementation of the eth-merkle-bridge",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aergoio/eth-merkle-bridge",
    packages=setuptools.find_packages(),
    install_requires=[
        "aergo-herapy==1.2.7",
        "web3==5.2.2",
        "merkle-bridge @ git+git://github.com/aergoio/merkle-bridge.git@50d2b315bc1dd00a5da93406476f4d8574f77a73#egg=merkle-bridge",
        "trie",
        "PyInquirer",
        "pyfiglet"
    ],
    classifiers=[
                "Programming Language :: Python :: 3.7",
                "License :: OSI Approved :: MIT License",
                "Operating System :: OS Independent",
            ],
)
