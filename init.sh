#!/bin/bash

ROOT="$( cd -P "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${ROOT}"

virtualenv virtualenv
./virtualenv/bin/pip install -r requirements.txt
