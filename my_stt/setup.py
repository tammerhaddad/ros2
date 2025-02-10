from setuptools import find_packages, setup

package_name = 'my_stt'

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
    maintainer='tammerhaddad',
    maintainer_email='tammerhaddad@todo.todo',
    description='TODO: Package description',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'stt = my_stt.my_stt:main',
        ],
    },
)
