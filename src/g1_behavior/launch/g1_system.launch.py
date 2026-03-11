from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        # 1. 运动控制节点（保持不变）
        Node(
            package="g1_motion",
            executable="motion_node"
        ),

        # 2. 核心修改：使用直连视频流的识别节点
        # 注意：这里我们调用的是写在 g1_camera 包里的新执行文件名
        Node(
            package="g1_camera",
            executable="face_node_direct",
            output="screen"  # 建议加上这一行，方便在终端看到识别出的名字
        ),

        # 3. 语音/动作响应节点（保持不变）
        Node(
            package="g1_behavior",
            executable="greeting_node"
        )
    ])