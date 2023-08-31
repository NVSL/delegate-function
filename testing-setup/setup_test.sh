#!/usr/bin/bash
SLURM_UID=990
SLURM_GID=990

MUNGE_UID=998
MUNGE_GID=995

groupadd -r --gid=$SLURM_GID slurm
useradd -r -g slurm --uid=$SLURM_UID slurm

groupadd -r --gid=$MUNGE_GID munge
useradd -r -g munge --uid=$MUNGE_UID munge

md5sum /etc/munge/munge.key
apt-get update --fix-missing; apt-get install -y slurm-client munge host
md5sum /etc/munge/munge.key

service munge start