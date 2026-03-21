from setuptools import find_packages, setup

package_name = 'g1_camera'

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
    description='G1 机器人相机包 - 处理机器人视频流解码和 USB 摄像头图像发布',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'face_node_direct = g1_camera.face_node_direct:main',
        ],
    },
)
