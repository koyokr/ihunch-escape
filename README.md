# ihunch-escape

## Docker
```sh
docker run --name ihunch --gpus device=0 -it -e DJANGO_SECRET_KEY=[generated key] -p 80:80 -p 443:443 koyokr/ihunch-escape
```

## Requirements
- CUDA 10.1 and CuDNN 7
- OpenCV 4.3.0
- Python 3.6
- PyTorch 1.6.0
- Detectron2
- XGBoost 1.1.1
- Django REST framework 3.11.1

## Fetch data
```sh
cd ihunch_escape/app/predictor/lightweight-human-pose-estimation-3d-demo.pytorch
python setup.py build_ext
sed -i 's/from models/from ..models/g' modules/*.py
sed -i 's/from modules/from ..modules/g' models/*.py
sed -i 's/from modules/from /g' modules/*.py
sed -i 's/from pose_extractor/from ..pose_extractor/g' */*.py
mv models modules pose_extractor/build/pose_extractor.so ..
```

```sh
cd ihunch_escape/app/predictor/
mkdir data
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1niBUbUecPhKt3GyeDNukobL4OQ3jqssH' -O data/human-pose-estimation-3d.pth
wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1DnQ9aUbkRBnfBTUGmD4ueT_zXsWmSKKQ' -O data/xgb-ihunch-prediction.bin
```

## Run server
```sh
export DJANGO_SECRET_KEY=[generated key]
cd ihunch_escape
python ./manage.py runserver 0.0.0.0:80
```
