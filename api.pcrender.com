server {
    server_name api.pcrender.com;

    access_log /var/log/nginx/api.pcrender.com.log;
    error_log /var/log/nginx/api.pcrender.com.err;

    location / {
        proxy_read_timeout 500s;
        proxy_connect_timeout 500s;
        proxy_send_timeout 500s;

        proxy_pass http://unix:/opt/pjt/app.sock;

    }

    listen 8000 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/api.pcrender.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/api.pcrender.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot

}

server {
    if ($host = api.pcrender.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    listen 80 default_server;
    server_name api.pcrender.com;
    return 404; # managed by Certbot


}
