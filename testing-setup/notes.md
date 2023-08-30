# Containerization Notes

## NFS Server

### Kernel Modules

On server host (outside docker)

`for i in nfs nfsd rpcsec_gss_krb5; do   sudo modprobe $i;done`

### To Start
`docker pull erichough/nfs-server`
`docker run -v /home/swanson/share:/tmp/files_to_share   -e NFS_EXPORT_0='/tmp/files_to_share                  *(rw,no_subtree_check)' --privileged  -p 2049:2049 erichough/nfs-server`

###  To Mount

`apt-get install nfs-common` -- this is overkill.  Tries to install server and want to upgrade the kernel etc.  Just need mount.nfs helper.
`sudo mount 172.17.0.2:/tmp/files_to_share /mnt/nfs`  -- needs mount.nfs helper