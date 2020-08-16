# ihunch-escape

## Docker
```sh
docker run --name ihunch \
    -it -d \
    --cpuset-cpus="0-3" \
    --gpus device=0 \
    -e DJANGO_SECRET_KEY="generated key" \
    -v /etc/letsencrypt:/etc/letsencrypt \
    -p 80:80 -p 443:443 \
    koyokr/ihunch-escape
```

## Requirements
- CUDA 10.1 and CuDNN 7
- OpenCV 4.3.0
- Python 3.6
- PyTorch 1.6.0
- Detectron2
- XGBoost 1.1.1
- Django REST framework 3.11.1
- Gunicorn 20.0.4
- Nginx
- Supervisord
