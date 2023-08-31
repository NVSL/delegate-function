#!/usr/bin/bash
SLURM_UID=990
SLURM_GID=990

MUNGE_UID=998
MUNGE_GID=995

pip install -e .

groupadd -r --gid=$SLURM_GID slurm
useradd -r -g slurm --uid=$SLURM_UID slurm

groupadd -r --gid=$MUNGE_GID munge
useradd -r -g munge --uid=$MUNGE_UID munge

groupadd cfiddlers
groupadd --gid 1001 docker_users
useradd -g cfiddlers -p fiddle -G docker_users -s /usr/bin/bash test_fiddler
yes '' | su test_fiddler ssh-keygen 
useradd -r -s /usr/sbin/nologin -u 7000 -G docker_users -p fiddle cfiddle 
#COPY ./testing-setup/cfiddle_sudoers /etc/sudoers.d

apt-get update --fix-missing; apt-get install -y slurm-client munge host

service munge start
