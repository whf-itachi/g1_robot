from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # 人脸识别节点
        Node(
            package="g1_face",
            executable="face_node"
        ),

        # 语音/动作响应节点
        Node(
            package="g1_behavior",
            executable="face_behavior_node"
        )
    ])
