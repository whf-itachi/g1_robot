from setuptools import find_packages, setup
import os

package_name = 'g1_face'

# 获取项目根目录（data 文件夹所在目录）
project_root = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data'
)

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # 安装人脸数据库到共享目录
        (os.path.join('share', package_name, 'data'), [
            os.path.join(project_root, 'face_database.json')
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Nathan',
    maintainer_email='service02@haitch.cn',
    description='G1 机器人人脸识别包 - 基于 InsightFace 的人脸检测和识别',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'face_node = g1_face.face_node:main',
        ],
    },
)
