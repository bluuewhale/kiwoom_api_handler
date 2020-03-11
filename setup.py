from setuptools import setup, find_packages

setup(
    name="kiwoom_api_handler",
    version="0.1.1",
    description="a package for hanlding Kiwoom OPEN API+ ActiveX Control with python",
    author="Donghyung Ko",
    author_email="koko8624@gmail.com",
    license="MIT",
    url="https://github.com/donghyungko/kiwoom_api_handler.git",
    download_url="https://github.com/DonghyungKo/kiwoom_api_handler/archive/master.zip",
    install_requires=["pandas==0.25.1", "PyQt5==5.14.1"],
    packages=find_packages(exclude=[]),
    keywords=["Kiwoom", "Kiwoom OPEN API+", "Kiwoom API", "키움증권"],
    python_requires=">=3.6",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    package_data={},
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
