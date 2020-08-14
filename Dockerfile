FROM ufoym/deepo:pytorch-py36-cu101

WORKDIR /root
RUN PIP_INSTALL="python -m pip --no-cache-dir install --upgrade" && \
    GIT_CLONE="git clone --depth 10" && \
    $PIP_INSTALL pycocotools && \
    $PIP_INSTALL detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu101/torch1.6/index.html && \
    $GIT_CLONE https://github.com/koyokr/ihunch-escape && \
    $GIT_CLONE https://github.com/Daniil-Osokin/lightweight-human-pose-estimation-3d-demo.pytorch \
        ihunch-escape/predictor/lightweight-human-pose-estimation-3d-demo.pytorch

WORKDIR /root/ihunch-escape/predictor/lightweight-human-pose-estimation-3d-demo.pytorch
RUN python setup.py build_ext && \
    sed -i 's/from models/from predictor.models/g' */*.py && \
    sed -i 's/from modules/from predictor.modules/g' */*.py && \
    sed -i 's/from pose_extractor/from predictor.pose_extractor/g' */*.py && \
    mv models modules pose_extractor/build/pose_extractor.so ..

WORKDIR /root/ihunch-escape/predictor
RUN rm -rf lightweight-human-pose-estimation-3d-demo.pytorch && \
    mkdir -p data && \
    wget --no-check-certificate \
        'https://docs.google.com/uc?export=download&id=1niBUbUecPhKt3GyeDNukobL4OQ3jqssH' \
        -O data/human-pose-estimation-3d.pth && \
    wget --no-check-certificate \
        'https://docs.google.com/uc?export=download&id=1DnQ9aUbkRBnfBTUGmD4ueT_zXsWmSKKQ' \
        -O data/xgb-ihunch-prediction.bin

WORKDIR /root/ihunch-escape
