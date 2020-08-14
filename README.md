# ihunch-escape
## Docker
```sh
docker build -t koyokr/ihunch-escape .
docker run --name ihunch --gpus all -it -p 80:80 -p 443:443 koyokr/ihunch-escape
```
