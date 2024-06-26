from pathlib import Path

import setuptools

from discourse_pm.__init__ import *

__short_description__ = 'PM Users on Discourse via API'

with Path('requirements.txt').open() as file_handle:
    __requirements__ = file_handle.read().splitlines()

setuptools.setup(
    name=__name__,
    version=__version__,
    author=__author__,
    author_email=__email__,
    description=__short_description__,
    long_description=__short_description__,
    long_description_content_type='text/plain',
    url=__github__,
    project_urls={
        'Bug Tracker': f'{__github__}/issues',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
    ],
    packages=setuptools.find_packages(),
    python_requires='>=3.8',
    install_requires=__requirements__,
    entry_points={'console_scripts': ['discourse-pm=discourse_pm.__main__:main']},
)
