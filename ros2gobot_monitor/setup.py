from setuptools import setup
import os

package_name = 'ros2gobot_monitor'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # ระบุชื่อไฟล์ launch ตรงๆ แทนการใช้ glob เพื่อป้องกัน Error
        (os.path.join('share', package_name, 'launch'), ['launch/monitor_server_launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='MT Robotics LP',
    maintainer_email='contact@mtrobotics.com',
    description='ROS2GO System Monitor Node',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # executable main
            'monitor_node = ros2gobot_monitor.monitor_node:main',
          
        ],
    },
)