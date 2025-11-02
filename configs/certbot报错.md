ww870411@instance-20250906-2216:~/25-26$ docker compose -f ww-certbot.yml up certbot
[+] Running 2/2
 ✔ Container phoenix-web-http-cert  R...                                   0.0s
 ✔ Container phoenix-certbot-once   Cr...                                  0.2s
Attaching to phoenix-certbot-once
phoenix-certbot-once  | Saving debug log to /var/log/letsencrypt/letsencrypt.log
phoenix-certbot-once  | Certbot doesn't know how to automatically configure the web server on this system. However, it can still get a certificate for you. Please run "certbot certonly" to do so. You'll need to manually configure your web server to use the resulting certificate.
phoenix-certbot-once exited with code 1
