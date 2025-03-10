from setuptools import find_packages, setup

package_name = 'trh_srvcli'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='tammerrh',
    maintainer_email='tammerrh@gmail.com',
    description='TODO: Package description',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'trh_srv = trh_srvcli.trh_srv:main',
            'trh_cli = trh_srvcli.trh_cli:main',
            'test_srv = trh_srvcli.test_srv:main',
        ],
    },
)
