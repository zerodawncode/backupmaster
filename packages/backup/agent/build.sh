#!/bin/bash

set -e

virtualenv virtualenv
source virtualenv/bin/activate
pip3.11 install -r requirements.txt
deactivate