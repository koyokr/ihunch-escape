FROM nvidia/cuda:11.2.2-cudnn8-runtime-ubuntu20.04
# ufoym/deepo
ENV LANG C.UTF-8
RUN APT_INSTALL="apt-get install -y --no-install-recommends" && \
    PIP_INSTALL="python -m pip --no-cache-dir install --upgrade" &&  \
    GIT_CLONE="git clone --depth 10" && \
    rm -rf /var/lib/apt/lists/* \
           /etc/apt/sources.list.d/cuda.list \
           /etc/apt/sources.list.d/nvidia-ml.list && \
    apt-get update && \
# ufoym/deepo: tools
    DEBIAN_FRONTEND=noninteractive $APT_INSTALL \
        build-essential \
        apt-utils \
        ca-certificates \
        wget \
        git \
        vim \
        libssl-dev \
        curl \
        unzip \
        unrar \
        cmake \
        && \
# ufoym/deepo: python
    DEBIAN_FRONTEND=noninteractive $APT_INSTALL \
        software-properties-common \
        && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive $APT_INSTALL \
        python3.7 \
        python3.7-dev \
        python3-distutils-extra \
        && \
    wget -O ~/get-pip.py \
        https://bootstrap.pypa.io/get-pip.py && \
    python3.7 ~/get-pip.py && \
    ln -s /usr/bin/python3.7 /usr/local/bin/python3 && \
    ln -s /usr/bin/python3.7 /usr/local/bin/python && \
    $PIP_INSTALL \
        setuptools \
        && \
# nginx, supervisor
    DEBIAN_FRONTEND=noninteractive $APT_INSTALL \
        nginx \
        supervisor \
        && \
# opencv
    DEBIAN_FRONTEND=noninteractive $APT_INSTALL \
        libatlas-base-dev \
        libgflags-dev \
        libgoogle-glog-dev \
        libhdf5-serial-dev \
        libleveldb-dev \
        liblmdb-dev \
        libprotobuf-dev \
        libsnappy-dev \
        protobuf-compiler \
        && \
    $PIP_INSTALL numpy && \
    $GIT_CLONE --branch 4.5.1 https://github.com/opencv/opencv ~/opencv && \
    mkdir -p ~/opencv/build && cd ~/opencv/build && \
    cmake -D CMAKE_BUILD_TYPE=RELEASE \
          -D CMAKE_INSTALL_PREFIX=/usr/local \
          -D WITH_1394=OFF \
          -D WITH_TBB=OFF \
          -D WITH_IPP=OFF \
          -D WITH_CUDA=OFF \
          -D WITH_OPENCL=OFF \
          -D WITH_QT=OFF \
          -D WITH_GTK=OFF \
          -D WITH_OPENGL=OFF \
          -D BUILD_WITH_DEBUG_INFO=OFF \
          -D BUILD_TESTS=OFF \
          -D BUILD_PERF_TESTS=OFF \
          -D BUILD_DOCS=OFF \
          -D BUILD_EXAMPLES=OFF \
          -D BUILD_NEW_PYTHON_SUPPORT=ON \
          -D BUILD_opencv_python3=ON \
          .. && \
    make -j"$(nproc)" install && \
    ln -s /usr/local/include/opencv4/opencv2 /usr/local/include/opencv2 && \
# torch, detectron2
    $PIP_INSTALL \
        torch==1.8.1+cu111 torchvision==0.9.1+cu111 torchaudio==0.8.1 -f \
        https://download.pytorch.org/whl/torch_stable.html && \
    $PIP_INSTALL \
        detectron2 -f \
        https://dl.fbaipublicfiles.com/detectron2/wheels/cu111/torch1.8/index.html && \
# cleanup
    cd / && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists/* /tmp/* ~/*
COPY . /project
WORKDIR /project
RUN PIP_INSTALL="python -m pip --no-cache-dir install --upgrade" && \
    GIT_CLONE="git clone --depth 10" && \
    WGET="wget -q --no-check-certificate" && \
# requirements
    $PIP_INSTALL -r requirements.txt && \
# lightweight-human-pose-estimation-3d-demo.pytorch
    $GIT_CLONE https://github.com/Daniil-Osokin/lightweight-human-pose-estimation-3d-demo.pytorch \
               ihunch_escape/app/predictor/lightweight-human-pose-estimation-3d-demo.pytorch && \
    cd ihunch_escape/app/predictor/lightweight-human-pose-estimation-3d-demo.pytorch && \
    python setup.py build_ext && \
    mv pose_extractor/build/pose_extractor.so .. && \
    cd .. && \
    rm -rf lightweight-human-pose-estimation-3d-demo.pytorch && \
# pretrained model
    $WGET 'https://docs.google.com/uc?export=download&id=1niBUbUecPhKt3GyeDNukobL4OQ3jqssH' -O \
          data/human-pose-estimation-3d.pth && \
    $WGET 'https://docs.google.com/uc?export=download&id=1DnQ9aUbkRBnfBTUGmD4ueT_zXsWmSKKQ' -O \
          data/xgb-ihunch-prediction.bin && \

RUN echo "daemon off;" >> /etc/nginx/nginx.conf
COPY config/nginx-app.conf /etc/nginx/sites-available/default
COPY config/supervisor-app-staging.conf /etc/supervisor/conf.d/

WORKDIR /project/ihunch_escape
CMD ["/bin/sh", "-c", "python manage.py collectstatic --noinput; python manage.py migrate --noinput; supervisord -n"]
EXPOSE 80 443
