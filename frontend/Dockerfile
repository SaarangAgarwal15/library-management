FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
HEALTHCHECK --interval=5s CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
