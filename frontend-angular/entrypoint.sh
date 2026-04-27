#!/bin/sh
echo "window.env = { BACKEND_URL: '$BACKEND_URL' };" > /usr/share/nginx/html/assets/env.js
exec "$@"
