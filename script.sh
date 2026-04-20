## Pull latest code
#git pull https://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@github.com/Bhaktam-Technologies/unlimited-astro-open.git main
#
## Build Docker image
#sudo docker build --build-arg configuration=development -t unlimited-astro-open .
#
## Remove existing container
#sudo docker rm -f unlimited-astro-open 2>/dev/null || true
#
## Run new container
#sudo docker run -d \
#  --name unlimited-astro-open \
#  --restart=always \
#  -v $PWD/logger:/app/logger \
#  --network host \
#  -e PYTHONUNBUFFERED=1 \
#  unlimited-astro-open:latest
#
## Apply crontab (if applicable)
## sudo crontab crontab_dev.txt