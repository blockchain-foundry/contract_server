#!/usr/bin/env python
import os
import sys
import environ

env = environ.Env(DEBUG=(bool, False),)  # set default values and casting
environ.Env.read_env()  # reading .env file

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", env("SERVER_CONFIG_ENV"))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
