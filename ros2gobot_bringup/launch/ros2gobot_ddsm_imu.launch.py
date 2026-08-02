# BSD 3-Clause License
#
# Copyright (c) 2023, Ekumen Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
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
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

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

    
    # ----------------------------------------------------
    # การเพิ่ม IMU Node (BNO08x)
    # ----------------------------------------------------
    pkg_bno086_driver = get_package_share_directory('bno086_driver')

    imu_config_file = os.path.join(
        pkg_bno086_driver, 
        'config',
        'bno085_uart_rvc.yaml'
    )

    imu_node = Node(
        package='bno086_driver',  
        executable='bno086_driver',  
        name='bno086_driver',
        output='screen',
        parameters=[imu_config_file]
    )

    # IMU สามารถเริ่มได้พร้อมกับเซ็นเซอร์อื่นๆ (3.0 วินาที)
    imu_timer = TimerAction(period=3.0, actions=[imu_node])


    # ----------------------------------------------------
    # การเพิ่ม EKF Node (robot_localization)
    # ----------------------------------------------------

    # ----------------------------------------------------
    # การเพิ่ม EKF Node (robot_localization)
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
        # Topic IMU ที่ใช้ใน EKF ควรเป็น Topic ที่เผยแพร่จาก imu_node นี้ (มักจะเป็น /imu/data)
    )

    # EKF ควรเริ่มหลังจาก ros2gobot_control และ IMU เริ่มทำงานและเผยแพร่ข้อมูลแล้ว (ตั้งค่าเป็น 6.0 วินาที)
    ekf_timer = TimerAction(period=6.0, actions=[ekf_node])
    

    # TODO(francocipollone): Improve concatenation of launch files.
    #
    # Waits for ros2gobot_description to set up robot_state_publisher.
    ros2gobot_control_timer = TimerAction(period=5.0, actions=[include_ros2gobot_control])
    # Defer sensors launch to avoid overhead while robot_state_publisher is setting up.
    #ydlidar_timer = TimerAction(period=3.0, actions=[include_ydlidar])
    #camera_timer = TimerAction(period=3.0, actions=[include_camera])

    return LaunchDescription([
        include_ros2gobot_description,
        ros2gobot_control_timer,
        odom_topic_arg,
        imu_timer,
        ekf_timer,
    
    ])
