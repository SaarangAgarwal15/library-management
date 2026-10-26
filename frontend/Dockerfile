FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
HEALTHCHECK --interval=15s CMD wget -qO- http://localhost/ >/dev/null || exit 1
