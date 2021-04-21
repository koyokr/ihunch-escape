docker run -it --rm --name certbot \
           -v ~/docker/etc/letsencrypt:/etc/letsencrypt \
           -v ~/docker/var/lib/letsencrypt:/var/lib/letsencrypt \
           certbot/certbot certonly
           --manual --preferred-challenges dns
