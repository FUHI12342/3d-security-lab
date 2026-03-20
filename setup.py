"""3D Security Lab セットアップスクリプト."""

from setuptools import find_packages, setup

setup(
    name="3d-security-lab",
    version="1.0.0",
    description="セキュリティ教育用3Dモデル解析キット",
    author="3D Security Lab Contributors",
    license="MIT",
    packages=find_packages(include=["tools", "tools.*"]),
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24.0",
        "Pillow>=10.0.0",
        "matplotlib>=3.7.0",
    ],
    extras_require={
        "webgl": ["playwright>=1.40.0"],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Topic :: Security",
        "Topic :: Multimedia :: Graphics :: 3D Rendering",
    ],
)
