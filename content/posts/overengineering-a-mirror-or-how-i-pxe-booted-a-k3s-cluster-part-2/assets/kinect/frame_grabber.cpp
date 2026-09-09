#include <iostream>
#include <cstdlib>
#include <signal.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <string.h>
#include <chrono>
#include <thread>
#include <unistd.h>
//#include <opencv2/opencv.hpp>
#include <libfreenect2/libfreenect2.hpp>
#include <libfreenect2/frame_listener_impl.h>
#include <libfreenect2/registration.h>
#include <libfreenect2/packet_pipeline.h>
#include <libfreenect2/logger.h>

// adapted from: https://github.com/OpenKinect/libfreenect2/pull/1197

// example usage: /usr/bin/frame_grabber 60 | ffplay -max_delay 0 -max_probe_packets 1 -analyzeduration 0 -flags +low_delay -fflags +nobuffer -f rawvideo -pixel_format bgra -video_size 1920x1080 -

bool protonect_shutdown = false;

void sigint_handler(int s)
{
  protonect_shutdown = true;
}

void write_frame(unsigned char *rgb_data, int width, int height)
{
  /*
  cv::Mat frame(height, width, CV_8UC4, rgb_data);
  cv::Mat bgr_frame;
  cv::cvtColor(frame, bgr_frame, cv::COLOR_BGRA2BGR);
  std::cout.write(reinterpret_cast<const char*>(bgr_frame.data), bgr_frame.total() * bgr_frame.elemSize());
  */
  size_t frame_size = width * height * 4; // 4 bytes per pixel (BGRA)
  std::cout.write(reinterpret_cast<const char*>(rgb_data), frame_size);
}

int main(int argc, char *argv[])
{
  // Maximum stdout optimizations
  std::ios_base::sync_with_stdio(false);
  std::cin.tie(nullptr);
  std::cout.tie(nullptr);
  
  // Set stdout to full buffering with large buffer for maximum throughput
  setvbuf(stdout, nullptr, _IOFBF, 65536);
  
  int max_fps = 0; // 0 means no limit
  
  // Parse command line arguments for FPS limit
  if (argc > 1) {
    max_fps = std::atoi(argv[1]);
    if (max_fps <= 0) {
      std::cerr << "Invalid FPS value: " << argv[1] << ". FPS must be positive." << std::endl;
      return -1;
    }
    std::cerr << "FPS limit set to: " << max_fps << std::endl;
  }

  auto frame_duration = std::chrono::microseconds(0);
  if (max_fps > 0) {
    frame_duration = std::chrono::microseconds(1000000 / max_fps);
  }

  libfreenect2::Freenect2 freenect2;
  libfreenect2::Freenect2Device *dev = nullptr;
  libfreenect2::PacketPipeline *pipeline = nullptr;

  libfreenect2::setGlobalLogger(libfreenect2::createConsoleLogger(libfreenect2::Logger::None));

  if (freenect2.enumerateDevices() == 0)
  {
    std::cerr << "No device connected!" << std::endl;
    return -1;
  }

  std::string serial = freenect2.getDefaultDeviceSerialNumber();

  dev = freenect2.openDevice(serial);

  if (dev == nullptr)
  {
    std::cerr << "Failure opening device!" << std::endl;
    return -1;
  }

  signal(SIGINT, sigint_handler);

  libfreenect2::SyncMultiFrameListener listener(libfreenect2::Frame::Color);
  libfreenect2::FrameMap frames;

  dev->setColorFrameListener(&listener);

  if (!dev->start())
    return -1;

  std::cerr << "Device serial: " << dev->getSerialNumber() << std::endl;
  std::cerr << "Device firmware: " << dev->getFirmwareVersion() << std::endl;

  auto last_frame_time = std::chrono::steady_clock::now();

  while (!protonect_shutdown)
  {
    if (!listener.waitForNewFrame(frames, 10 * 1000)) // 10 seconds
    {
      std::cerr << "Timeout!" << std::endl;
      return -1;
    }
    
    // FPS limiting logic
    if (max_fps > 0) {
      auto current_time = std::chrono::steady_clock::now();
      auto elapsed = current_time - last_frame_time;
      
      if (elapsed < frame_duration) {
        std::this_thread::sleep_for(frame_duration - elapsed);
      }
      last_frame_time = std::chrono::steady_clock::now();
    }
    
    libfreenect2::Frame *rgb = frames[libfreenect2::Frame::Color];

    write_frame(rgb->data, rgb->width, rgb->height);

    listener.release(frames);
  }

  dev->stop();
  dev->close();
  return 0;
}