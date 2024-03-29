
from setuptools import setup, find_packages


setup(name='x-mroy-13',
    version='0.0.0',
    description='None',
    url='https://github.com/xxx',
    author='auth',
    author_email='xxx@gmail.com',
    license='MIT',
    include_package_data=True,
    zip_safe=False,
    packages=find_packages(),
    install_requires=['termcolor', 'asyncssh', 'x_menu','geoip2'],
    entry_points={
        'console_scripts': ['Seed-node=MapHack_src.cmd:main', 'Seed-ui=MapHack_ui.main:main']
    },

)
