
CMAKE_MINIMUM_REQUIRED(VERSION 2.8.12.1)

if(WIN32 AND NOT MINGW)
  if(NOT DEFINED CMAKE_DEBUG_POSTFIX)
    set(CMAKE_DEBUG_POSTFIX "d")
  endif()
endif()

IF(NOT DEFINED CMAKE_BUILD_TYPE)
  # No effect for multi-configuration generators (e.g. for Visual Studio)
  SET(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "Choose: RelWithDebInfo Release Debug MinSizeRel None")
ENDIF()

PROJECT(frame_grabber)

SET(MY_DIR ${libfreenect2_examples_SOURCE_DIR})
SET(DEPENDS_DIR "${MY_DIR}/../depends" CACHE STRING "Dependency directory")

OPTION(ENABLE_OPENGL "Enable OpenGL support" ON)

# The example build system is standalone and will work out-of-tree with these files copied
SET(freenect2_ROOT_DIR ${MY_DIR}/../..)
SET(flextGL_SOURCES ${freenect2_ROOT_DIR}/src/flextGL.cpp)
SET(flextGL_INCLUDE_DIRS ${freenect2_ROOT_DIR}/src) # for flextGL.h

FIND_PACKAGE(PkgConfig)    # try find PKGConfig as it will be used if found
LIST(APPEND CMAKE_MODULE_PATH ${freenect2_ROOT_DIR}/cmake_modules) # FindGLFW3.cmake

FIND_PACKAGE(OpenCV REQUIRED)
SET(RESOURCES_INC_FILE "${PROJECT_BINARY_DIR}/resources.inc.h")

IF(TARGET freenect2)
  MESSAGE(STATUS "Using in-tree freenect2 target")
  SET(freenect2_LIBRARIES freenect2)
  SET(freenect2_DLLS ${LIBFREENECT2_DLLS})
ELSE()
  FIND_PACKAGE(freenect2 REQUIRED)
  # Out-of-tree build will have to have DLLs manually copied.
ENDIF()


INCLUDE_DIRECTORIES(
  "/usr/include/opencv4"
  ${freenect2_INCLUDE_DIR}
)
add_compile_options(-fexceptions)
SET(frame_grabber_src
  frame_grabber.cpp
)

SET(frame_grabber_LIBRARIES
  ${freenect2_LIBRARIES}
)

SET(frame_grabber_DLLS
  ${freenect2_DLLS}
)

ADD_EXECUTABLE(frame_grabber
  ${frame_grabber_src}
)

TARGET_LINK_LIBRARIES(frame_grabber
  ${frame_grabber_LIBRARIES}
  opencv_core
  opencv_highgui
  ${OpenCV_LIBS}
)

IF(WIN32)
  INSTALL(TARGETS frame_grabber DESTINATION bin)
  LIST(REMOVE_DUPLICATES frame_grabber_DLLS)
  FOREACH(FILEI ${frame_grabber_DLLS})
    ADD_CUSTOM_COMMAND(TARGET frame_grabber POST_BUILD
      COMMAND ${CMAKE_COMMAND} -E copy_if_different ${FILEI} $<TARGET_FILE_DIR:frame_grabber>
    )
  ENDFOREACH(FILEI)
INSTALL(TARGETS frame_grabber DESTINATION bin)
  INSTALL(FILES ${frame_grabber_DLLS} DESTINATION bin)
ENDIF()
INSTALL(TARGETS frame_grabber DESTINATION bin)
