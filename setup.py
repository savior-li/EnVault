from setuptools import setup, find_packages

setup(
    name="backup-tool",
    version="1.0.0",
    description="DevEnv Backup Tool - 开发环境备份、快照、上传网盘一体化工具",
    author="savior-li",
    author_email="savior@example.com",
    url="https://github.com/savior-li/backup-tool",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.9",
        ],
    },
    entry_points={
        "console_scripts": [
            "backup-tool=backup_tool:main",
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
    ),
    python_requires=">=3.8",
)