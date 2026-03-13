# Install script for directory: /opt/nordic/ncs/v3.2.1/zephyr

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/usr/local")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "TRUE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/opt/nordic/ncs/toolchains/322ac893fe/opt/zephyr-sdk/arm-zephyr-eabi/bin/arm-zephyr-eabi-objdump")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/arch/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/lib/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/soc/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/boards/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/subsys/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/drivers/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/nrf/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/hostap/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/mcuboot/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/mbedtls/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/trusted-firmware-m/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/cjson/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/azure-sdk-for-c/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/cirrus-logic/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/openthread/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/memfault-firmware-sdk/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/canopennode/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/chre/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/lz4/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/zscilib/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/cmsis/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/cmsis-dsp/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/cmsis-nn/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/cmsis_6/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/fatfs/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/hal_nordic/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/hal_st/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/hal_tdk/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/hal_wurthelektronik/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/liblc3/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/libmetal/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/littlefs/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/loramac-node/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/lvgl/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/mipi-sys-t/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/nanopb/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/nrf_wifi/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/open-amp/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/percepio/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/picolibc/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/segger/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/uoscore-uedhoc/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/zcbor/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/nrfxlib/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/nrf_hw_models/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/modules/connectedhomeip/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/kernel/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/cmake/flash/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/cmake/usage/cmake_install.cmake")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for the subdirectory.
  include("/Users/javierruizhurtado/Documents/WorkspaceSAC/brazo_robotico/build/brazo_robotico/zephyr/cmake/reports/cmake_install.cmake")
endif()

