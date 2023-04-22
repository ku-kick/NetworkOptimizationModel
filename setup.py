from setuptools import setup

setup(
    name="twoopt",
    packages=[
        "twoopt",
        "twoopt.data_processing",
        "twoopt.optimization",
        "twoopt.simulation",
        "twoopt.utility",
    ],
    include_package_data=True,
    license="MIT",
    description="Algorithms for network optimization",
    long_description="",
    author="Dmitry Murashov",
    setup_requires=["wheel"],
    install_requires=[
        "pandas",
        "numpy==1.23.2",
        "scipy",
        "simpy",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Inependent",
    ],
    python_requires=">=3.7",
    version="0.8.0",
)

