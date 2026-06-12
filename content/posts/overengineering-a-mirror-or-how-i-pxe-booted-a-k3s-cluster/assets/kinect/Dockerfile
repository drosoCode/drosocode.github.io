FROM debian:13-slim AS builder

RUN apt-get update && apt-get install -y build-essential git cmake opencl-headers pkg-config libjpeg62-turbo-dev libturbojpeg0-dev libusb-1.0-0-dev libglfw3-dev ocl-icd-opencl-dev libopencv-dev

RUN git clone https://github.com/OpenKinect/libfreenect2 /tmp/libfreenect2 && \
	cd /tmp/libfreenect2/ && git checkout fd64c5d9b214df6f6a55b4419357e51083f15d93

COPY frame_grabber /tmp/libfreenect2/examples/frame_grabber

RUN cd /tmp/libfreenect2 && mkdir build && cd build && \
    echo "ADD_SUBDIRECTORY(\${MY_DIR}/examples/frame_grabber)" >> ../CMakeLists.txt && \
	sed --debug -i -e 's:const int CL_ICDL_VERSION:// const int CL_ICDL_VERSION:' "../src/opencl_depth_packet_processor.cpp" "../src/opencl_kde_depth_packet_processor.cpp" && \
	cmake ".." \
		-DCMAKE_INSTALL_PREFIX=/usr \
		-DCMAKE_BUILD_TYPE=Release \
		-DENABLE_CXX11=ON \
		-DENABLE_OPENCL=ON \
		-DENABLE_OPENGL=OFF \
		-DENABLE_CUDA=OFF \
		-DBUILD_EXAMPLES=OFF \
		-DBUILD_SHARED_LIBS=OFF \
		-DCMAKE_POLICY_VERSION_MINIMUM=3.5 && \
	make

FROM debian:13-slim

RUN apt-get update && apt-get install -y ffmpeg libturbojpeg0 libglfw3

COPY --from=builder /tmp/libfreenect2/build/bin/frame_grabber /app/frame_grabber

COPY launch.sh /app/launch.sh

RUN chmod +x /app/launch.sh

CMD ["/app/launch.sh"]
