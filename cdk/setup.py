import setuptools

with open("README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="stock_analysis",
    version="0.1.0",
    description="Stock Analysis Application CDK",
    author="jmoussa",
    package_dir={"": "backend"},
    packages=setuptools.find_packages(where="backend"),
    install_requires=[
        "aws-cdk-lib==2.118.0",
        "constructs>=10.0.0",
    ],
    python_requires=">=3.9",
)
