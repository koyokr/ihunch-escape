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
    -v /etc/letsencrypt:/etc/letsencrypt \
    -p 443:443 \
    koyokr/ihunch-escape
```

## Requirements
- CUDA 10.1 and CuDNN 7 (GeForce RTX 2080 Ti)
- OpenCV 4.3.0
- Python 3.6
- PyTorch 1.6.0
- Detectron2
- XGBoost 1.1.1
- Django REST framework 3.11.1
- Gunicorn 20.0.4
- Nginx
- Supervisord
