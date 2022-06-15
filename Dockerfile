FROM python:3.10-alpine

WORKDIR /app
RUN apk add --update supervisor && rm -rf /tmp/* /var/cache/apk/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY . .

EXPOSE 443
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]