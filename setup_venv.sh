#!/bin/sh
#
# setup_venv.sh is a script to create a virtual environment.
# it will create a virtual environment in env directory and
# install all packages listed in requirements.txt
#
# Usage:
#     ./setup_venv.sh
#
ORIGIN=$(dirname "$0")
PATH_pygcointools=$ORIGIN/pygcointools

# check whether venv works
virtualenv_module="venv"
. /etc/os-release
if ([ "$ID" == "rhel" ] || [[ "$ID_LIKE" =~ "rhel" ]]) && [ "$VERSION_ID" == "7" ]; then
    if ! python3 -m "$virtualenv_module" $ORIGIN/env; then
        rm -r $ORIGIN/env
        echo "Install venv failed."
        echo "Change to install virtualenv."
        if !(command -v pip3 > /dev/null 2>&1); then
            echo "pip3 is not installed. We are going to install it."
            curl https://bootstrap.pypa.io/get-pip.py | python3 - --user
            rm -f ~/.local/bin/easy_install
            rm -f ~/.local/bin/pip
            rm -f ~/.local/bin/wheel
        fi
        pip3 install --user virtualenv
        virtualenv_module="virtualenv"
        python3 -m "$virtualenv_module" $ORIGIN/env
    fi
fi

. $ORIGIN/env/bin/activate

# install required packages
pip install -e $PATH_pygcointools
pip install -r requirements.txt
