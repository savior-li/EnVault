from setuptools import setup, find_packages

setup(
    name="envault",
    version="1.1.0",
    description="EnVault - DevEnv Backup Tool with encryption, multi-directory, and multi-cloud support",
    author="savior-li",
    author_email="savior@monkeycode.ai",
    url="https://github.com/savior-li/backup-tool",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.25.0",
        "pyyaml>=5.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "envault=envault:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)