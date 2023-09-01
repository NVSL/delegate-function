#!/usr/bin/bash

ssh-keygen -f "/home/test_fiddler/.ssh/known_hosts" -R "ssh-host"
ssh-keygen -f "/root/.ssh/known_hosts" -R "ssh-host"

for u in test_fiddler jovyan; do 
    ssh-keygen -f "/home/$u/.ssh/known_hosts" -R "ssh-host"
    chown $u -R /home/$u/.ssh/
done    