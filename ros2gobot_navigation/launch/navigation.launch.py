# Copyright (c) 2021 Juan Miguel Jimeno
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node

def generate_launch_description():
    nav2_launch_path = PathJoinSubstitution(
        [FindPackageShare('nav2_bringup'), 'launch', 'bringup_launch.py']
    )

    rviz_config_path = PathJoinSubstitution(
        [FindPackageShare('ros2gobot_navigation'), 'rviz', 'ros2gobot_navigation.rviz']
    )

    nav2_config_path = PathJoinSubstitution(
        [FindPackageShare('ros2gobot_navigation'), 'config', 'navigation.yaml']
    )

    # กำหนด Path หลักสำหรับโฟลเดอร์เก็บ Map
    MAP_DIR = '/opt/ros2go/maps/'

    # ใช้ PythonExpression เพื่อตรวจสอบ:
    # ถ้าพิมพ์มาแค่ชื่อไฟล์ (เช่น my_map.yaml) ระบบจะเติม /opt/ros2go/maps/ ให้ด้านหน้า
    # แต่ถ้าพิมพ์ Path เต็มมา (มี / นำหน้า) ระบบจะใช้ค่านั้นเลย
    map_full_path = PythonExpression([
        f"'{MAP_DIR}' + '", LaunchConfiguration("map"),
        "' if not '", LaunchConfiguration("map"), "'.startswith('/') else '", LaunchConfiguration("map"), "'"
    ])

    return LaunchDescription([
        DeclareLaunchArgument(
            name='sim', 
            default_value='false',
            description='Enable use_sim_time to true'
        ),

        DeclareLaunchArgument(
            name='rviz', 
            default_value='false',
            description='Run rviz'
        ),

        DeclareLaunchArgument(
            name='map', 
            default_value='my_map.yaml', # ตั้งค่าเริ่มต้นเป็นแค่ชื่อไฟล์
            description='Navigation map file name (will automatically look in /opt/ros2go/maps/)'
        ),

        DeclareLaunchArgument(
            name='initial_pose_x',
            default_value='0.5',
            description='Initial robot X position'
        ),

        DeclareLaunchArgument(
            name='initial_pose_y',
            default_value='0.0',
            description='Initial robot Y position'
        ),

        DeclareLaunchArgument(
            name='initial_pose_yaw',
            default_value='0.0',
            description='Initial robot yaw'
        ),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_launch_path),
            launch_arguments={
                'map': map_full_path, # ส่ง path ที่ประมวลผลแล้วเข้าไป
                'use_sim_time': LaunchConfiguration("sim"),
                'params_file': nav2_config_path,
                'initial_pose_x': LaunchConfiguration('initial_pose_x'),
                'initial_pose_y': LaunchConfiguration('initial_pose_y'),
                'initial_pose_yaw': LaunchConfiguration('initial_pose_yaw')
            }.items()
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config_path],
            condition=IfCondition(LaunchConfiguration("rviz")),
            parameters=[{'use_sim_time': LaunchConfiguration("sim")}]
        )
    ])