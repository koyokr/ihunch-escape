# ihunch-escape
## Docker
```sh
docker build -t koyokr/ihunch-escape .
docker run --name ihunch --gpus device=0 -it -e DJANGO_SECRET_KEY=[generated key] -p 80:80 -p 443:443 koyokr/ihunch-escape
```
