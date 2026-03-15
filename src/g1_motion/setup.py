from setuptools import find_packages, setup

package_name = 'g1_motion'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Nathan',
    maintainer_email='service02@haitch.cn',
    description='G1 机器人运动控制包 - 基于 unitree_sdk2py 的动作执行和控制',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'motion_node = g1_motion.motion_node:main',
            'g1_debug = g1_motion.g1_debug_node:main',
        ],
    },
)
