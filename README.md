# ihunch-escape
Thanks!
- <https://github.com/Daniil-Osokin/lightweight-human-pose-estimation-3d-demo.pytorch>
- <https://github.com/elastic7327/django-gunicorn-nginx-docker>
- <https://github.com/cr4zyd3v/django-docker-ssl>

## Usage
```py
from requests import post
r = post('https://api.ihunch.koyo.io/upload', files={'file': open('demo.jpg', 'rb')})
d = r.json()
if d['human']:
    print('ihunch:', d['pred'])
```

## Docker
```sh
docker run --name ihunch \
    -it -d \
    --gpus device=0 \
    -e DJANGO_SECRET_KEY="generated key" \
    -v ~/docker/etc/letsencrypt:/etc/letsencrypt \
    -p 443:443 \
    koyokr/ihunch-escape
```

## Requirements
- CUDA 11.2 and CuDNN 8 (GeForce RTX 3080)
- OpenCV 4.5.1
- Python 3.7
- PyTorch 1.8.1
- Detectron2 0.4
- XGBoost 1.4.1
- Django REST framework 3.12.4
- Gunicorn 20.1.0
- Nginx 1.18.0
- Supervisord 4.1.0
