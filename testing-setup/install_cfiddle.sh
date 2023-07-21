#!/usr/bin/env bash
set -ex

git clone -b devel http://github.com/NVSL/cfiddle
cd cfiddle; pip install cfiddle -e 
cfiddle_install_prereqs.sh

