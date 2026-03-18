from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # 1. 运动控制节点
        Node(
            package="g1_motion",
            executable="motion_node"
        ),

        # 2. USB 摄像头节点
        Node(
            package="g1_camera",
            executable="face_node_direct"
        ),

        # 3. 人脸识别节点
        Node(
            package="g1_face",
            executable="face_node"
        ),

        # 4. 语音/动作响应节点
        Node(
            package="g1_behavior",
            executable="face_behavior_node"
        )
    ])
