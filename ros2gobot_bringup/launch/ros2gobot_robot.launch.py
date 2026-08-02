# BSD 3-Clause License
# Copyright (c) 2023, Ekumen Inc.
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, RegisterEventHandler, EmitEvent
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown

# Obtains share directory paths.
pkg_ros2gobot_bringup = get_package_share_directory('ros2gobot_bringup')
pkg_ros2gobot_control = get_package_share_directory('ros2gobot_control')
pkg_ros2gobot_description = get_package_share_directory('ros2gobot_description')

def generate_launch_description():
    odom_topic_arg = DeclareLaunchArgument(
                name='odom_topic', 
                default_value='/odom',
                description='EKF out odometry topic'
            )
    odom_topic = LaunchConfiguration('odom_topic')

    rplidar_arg = DeclareLaunchArgument(
            'include_rplidar',
            default_value='True',
            description='Indicates whether to include rplidar launch.')
    rplidar =  LaunchConfiguration('include_rplidar')
    
    # [NEW]   launch      laser_range_filter (default True)
    laser_range_filter_arg = DeclareLaunchArgument(
            'laser_range_filter',
            default_value='True',
            description='Enable laser scan filtering')
    laser_range_filter = LaunchConfiguration('laser_range_filter')
            
    # Includes ros2gobot_description launch file
    include_ros2gobot_description = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros2gobot_description, 'launch', 'ros2gobot_description.launch.py'),
        ),
    )

    # Include ros2gobot_control launch file
    include_ros2gobot_control =  IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros2gobot_control, 'launch', 'ros2gobot_control.launch.py'),
        ),
        launch_arguments={
        }.items()
    )

    # Include rplidar launch file
    include_rplidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros2gobot_bringup, 'launch', 'rplidar.launch.py'),
        ),
        launch_arguments={
            "serial_port": '/dev/tty_lidar',
            "laser_range_filter": laser_range_filter, # [NEW]   Lidar launch 
        }.items(),
            condition=IfCondition(rplidar)
    )
    
    # ----------------------------------------------------
    #   IMU Node (BNO08x)
    # ----------------------------------------------------
    pkg_bno086_driver = get_package_share_directory('bno086_driver')
    imu_config_file = os.path.join(
        pkg_bno086_driver, 
        'config',
        'bno086_uart_rvc.yaml'
    )

    imu_node = Node(
        package='bno086_driver',  
        executable='bno086_driver',  
        name='bno086_driver',
        output='screen',
        parameters=[imu_config_file]
    )
    # IMU   (3.0 
    imu_timer = TimerAction(period=3.0, actions=[imu_node])

    # ----------------------------------------------------
    #   EKF Node (robot_localization)
    # ----------------------------------------------------
    ekf_config_file = os.path.join(
        pkg_ros2gobot_bringup, 'config', 'ekf.yaml'
    )
    
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[ekf_config_file],
        remappings=[("odometry/filtered",odom_topic)]
    )
    # EKF   ros2gobot_control   IMU   6.0 
    ekf_timer = TimerAction(period=6.0, actions=[ekf_node])

    # ----------------------------------------------------
    #   RF2O Laser Odometry Node
    # ----------------------------------------------------
    rf2o_node = Node(
        package='rf2o_laser_odometry',
        executable='rf2o_laser_odometry_node',
        name='rf2o_laser_odometry',
        output='screen',
        parameters=[{
            'laser_scan_topic': '/scan',
            'odom_topic': '/odom_rf2o',
            'publish_tf': False,
            'base_frame_id': 'base_footprint',
            'odom_frame_id': 'odom',
            'init_pose_from_topic': '',
            'freq': 10.0
        }],
        arguments=['--ros-args', '--log-level', 'error']
    )
    
    # ----------------------------------------------------
    # Global Error Handler
    # ----------------------------------------------------
    def handle_process_exit(event, context):
        if event.returncode != 0 and event.returncode is not None:
            return EmitEvent(
                event=Shutdown(reason=f'\n\n[FATAL ERROR] Process exited with code {event.returncode}! Shutting down entire launch system.\n')
            )
        return None

    global_shutdown_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            on_exit=handle_process_exit
        )
    )
    
    # ----------------------------------------------------
    # ROS2GO Monitor, API Server   Rosbridge
    # ----------------------------------------------------
    ros2gobot_monitor_node = Node(
        package='ros2gobot_monitor',
        executable='monitor_node',
        name='ros2gobot_monitor',
        output='screen'
    )
  
    rosbridge_websocket_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        output='screen',
        parameters=[{'port': 9090}]
    )

    # ----------------------------------------------------
    # Waits for ros2gobot_description to set up robot_state_publisher.
    ros2gobot_control_timer = TimerAction(period=5.0, actions=[include_ros2gobot_control])

    # Defer sensors launch to avoid overhead while robot_state_publisher is setting up.
    rplidar_timer = TimerAction(period=3.0, actions=[include_rplidar])

    return LaunchDescription([
        global_shutdown_handler, 
        include_ros2gobot_description,
        ros2gobot_control_timer,
        odom_topic_arg,
        imu_timer,
        ekf_timer,
        rplidar_arg,
        laser_range_filter_arg,      # [NEW] Argument   Filter
        rplidar_timer,
        rf2o_node,                   # [NEW] RF2O Node
        ros2gobot_monitor_node,      # Node 
        rosbridge_websocket_node,    # Node   WebSocket
    ])