#!/bin/bash

# ==========================================
# ROS 2 Jazzy Jalisco Installation Script
# Based on: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html
# Package: ros-jazzy-ros-base + ros-dev-tools + cyclonedds
# ==========================================

set -e

echo "=== 1. Checking and Setting Locale ==="
locale
sudo apt update && sudo apt install locales -y
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
locale

echo "=== 2. Enabling Universe Repository and ROS 2 APT Source ==="
sudo apt install software-properties-common -y
sudo add-apt-repository universe -y

sudo apt update && sudo apt install curl -y
export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb

echo "=== 3. Installing Development Tools (ros-dev-tools) ==="
sudo apt update && sudo apt upgrade -y
sudo apt install ros-dev-tools -y

echo "=== 4. Installing ROS 2 Jazzy (ros-jazzy-ros-base) ==="
sudo apt install ros-jazzy-ros-base -y

echo "=== 5. Installing Cyclone DDS ==="
sudo apt install ros-jazzy-rmw-cyclonedds-cpp -y

echo "=== 6. Setting up Environment ==="
if ! grep -q "/opt/ros/jazzy/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
    echo "Added ROS 2 Jazzy setup to ~/.bashrc"
fi

if ! grep -q "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" ~/.bashrc; then
    echo "export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp" >> ~/.bashrc
    echo "Added RMW_IMPLEMENTATION to ~/.bashrc"
fi

echo "=== Installation Completed Successfully! ==="
echo "Please restart your terminal or run: source ~/.bashrc"
