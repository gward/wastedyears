import setuptools

install_requires = [
    'click >= 8.1',
    'SQLAlchemy >= 1.4',
]
dev_requires = [
    'pyflakes >= 2.4.0',
    'pycodestyle >= 2.8.0',
    'mypy >= 0.961',
]

setuptools.setup(
    name='wastedyears',
    version='0.0.1',
    packages=setuptools.find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires,
    },
    entry_points={
        'console_scripts': [
            'wyr = wyr.cli:main',
        ],
    },
)
