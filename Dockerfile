FROM ufoym/deepo:all-py36-cu101

WORKDIR /root
RUN PIP_INSTALL="python -m pip --no-cache-dir install --upgrade" && \
    GIT_CLONE="git clone --depth 10" && \
    $PIP_INSTALL torch==1.6.0+cu101 torchvision==0.7.0+cu101 -f https://download.pytorch.org/whl/torch_stable.html && \
    $PIP_INSTALL detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cu101/torch1.6/index.html && \
    $GIT_CLONE https://github.com/koyokr/ihunch-escape && \
    $PIP_INSTALL -r ihunch-escape/requirements.txt && \
    $GIT_CLONE https://github.com/Daniil-Osokin/lightweight-human-pose-estimation-3d-demo.pytorch \
        ihunch-escape/predictor/lightweight-human-pose-estimation-3d-demo.pytorch

WORKDIR /root/ihunch-escape/predictor/lightweight-human-pose-estimation-3d-demo.pytorch
RUN python setup.py build_ext && \
    sed -i 's/from models/from ..models/g' modules/*.py && \
    sed -i 's/from modules/from ..modules/g' models/*.py && \
    sed -i 's/from modules/from ./g' modules/*.py && \
    sed -i 's/from pose_extractor/from ..pose_extractor/g' */*.py && \
    mv models modules pose_extractor/build/pose_extractor.so ..

WORKDIR /root/ihunch-escape/predictor
RUN WGET="wget -q --no-check-certificate" && \
    rm -rf lightweight-human-pose-estimation-3d-demo.pytorch && \
    mkdir -p data && \
    $WGET 'https://docs.google.com/uc?export=download&id=1niBUbUecPhKt3GyeDNukobL4OQ3jqssH' \
        -O data/human-pose-estimation-3d.pth && \
    $WGET 'https://docs.google.com/uc?export=download&id=1DnQ9aUbkRBnfBTUGmD4ueT_zXsWmSKKQ' \
        -O data/xgb-ihunch-prediction.bin

WORKDIR /root/ihunch-escape
RUN mv predictor uploadapp
