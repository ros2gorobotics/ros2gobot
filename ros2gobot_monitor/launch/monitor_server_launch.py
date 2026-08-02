from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ros2gobot_monitor',
            executable='api_server',
            name='api_server_node',
            output='screen'
        )
    ])