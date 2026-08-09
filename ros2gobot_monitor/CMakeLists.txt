cmake_minimum_required(VERSION 3.8)
project(ros2gobot_monitor)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ค้นหา Dependencies ที่จำเป็น (เหมือนการ import ใน Python)
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(ros2gobot_msgs REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2_msgs REQUIRED)

# สร้างไฟล์รันโปรแกรม (Executable) จากโค้ด C++
add_executable(monitor_node src/monitor_node.cpp)

# เชื่อมต่อ Dependencies เข้ากับ Executable
ament_target_dependencies(monitor_node
  rclcpp
  ros2gobot_msgs
  rcl_interfaces
  sensor_msgs
  nav_msgs
  tf2_msgs
)

# กำหนดตำแหน่งติดตั้ง
install(TARGETS
  monitor_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
