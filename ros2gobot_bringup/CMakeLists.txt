cmake_minimum_required(VERSION 3.8)
project(ros2gobot_bringup)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY
    config
    launch
    rviz
  DESTINATION
    share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/robot
  DESTINATION bin
)

ament_package()
