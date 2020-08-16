FROM ufoym/deepo:pytorch-py36-cu101

RUN APT_INSTALL="apt-get install -y --no-install-recommends" && \
    GIT_CLONE="git clone --depth 10" && \
    apt-get update && \
# nginx, supervisor
    DEBIAN_FRONTEND=noninteractive $APT_INSTALL \
        nginx && \
        supervisor && \
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
    $GIT_CLONE --branch 4.3.0 https://github.com/opencv/opencv ~/opencv && \
    mkdir -p ~/opencv/build && cd ~/opencv/build && \
    cmake -D CMAKE_BUILD_TYPE=RELEASE \
          -D CMAKE_INSTALL_PREFIX=/usr/local \
          -D WITH_IPP=OFF \
          -D WITH_CUDA=OFF \
          -D WITH_OPENCL=OFF \
          -D BUILD_TESTS=OFF \
          -D BUILD_PERF_TESTS=OFF \
          -D BUILD_DOCS=OFF \
          -D BUILD_EXAMPLES=OFF \
          .. && \
    make -j"$(nproc)" install && \
    ln -s /usr/local/include/opencv4/opencv2 /usr/local/include/opencv2 && \
# cleanup
    cd / && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists/* /tmp/* ~/*

COPY . /project
WORKDIR /project
RUN PIP_INSTALL="python -m pip --no-cache-dir install --upgrade" && \
    WGET="wget -q --no-check-certificate" && \
    $PIP_INSTALL pip && \
# requirements, pytorch, detectron2
    $PIP_INSTALL -r requirements.txt && \
    $PIP_INSTALL \
        torch==1.6.0+cu101 torchvision==0.7.0+cu101 -f \
        https://download.pytorch.org/whl/torch_stable.html && \
    $PIP_INSTALL \
        detectron2 -f \
        https://dl.fbaipublicfiles.com/detectron2/wheels/cu101/torch1.6/index.html && \
# lightweight-human-pose-estimation-3d-demo.pytorch
    git submodule init && git submodule update && \
    cd ihunch_escape/app/predictor/lightweight-human-pose-estimation-3d-demo.pytorch && \
    python setup.py build_ext && \
    sed -i 's/from models/from ..models/g' modules/*.py && \
    sed -i 's/from modules/from ..modules/g' models/*.py && \
    sed -i 's/from modules/from /g' modules/*.py && \
    sed -i 's/from pose_extractor/from ..pose_extractor/g' */*.py && \
    mv models modules pose_extractor/build/pose_extractor.so .. && \
    cd .. && \
    rm -rf lightweight-human-pose-estimation-3d-demo.pytorch && \
# fetch data
    $WGET \
        'https://docs.google.com/uc?export=download&id=1niBUbUecPhKt3GyeDNukobL4OQ3jqssH' -O \
        data/human-pose-estimation-3d.pth && \
    $WGET \
        'https://docs.google.com/uc?export=download&id=1DnQ9aUbkRBnfBTUGmD4ueT_zXsWmSKKQ' -O \
        data/xgb-ihunch-prediction.bin

RUN echo "daemon off;" >> /etc/nginx/nginx.conf
COPY config/nginx-app.conf /etc/nginx/sites-available/default
COPY config/supervisor-app-staging.conf /etc/supervisor/conf.d/

CMD ["supervisord", "-n"]
EXPOSE 80 443
