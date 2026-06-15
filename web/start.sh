#!/bin/sh
GA4="${GA4_MEASUREMENT_ID:-G-XXXXXXXXXX}"
sed -i "s/GA4_MEASUREMENT_ID_PLACEHOLDER/${GA4}/g" /usr/share/nginx/html/index.html
exec nginx -g 'daemon off;'
