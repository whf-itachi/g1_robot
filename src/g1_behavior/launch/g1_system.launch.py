from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    return LaunchDescription([

        Node(
            package="g1_motion",
            executable="motion_node"
        ),

        Node(
            package="g1_camera",
            executable="camera_node"
        ),

        Node(
            package="g1_face",
            executable="face_node"
        ),

        Node(
            package="g1_behavior",
            executable="greeting_node"
        )

    ])
