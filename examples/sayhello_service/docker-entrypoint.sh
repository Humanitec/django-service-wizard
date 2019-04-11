#!/bin/bash

# It is responsability of the deployment orchestration to execute before
# migrations, create default admin user, populate minimal data, etc.

gunicorn sayhello_service.wsgi --config sayhello_service/gunicorn_conf.py
