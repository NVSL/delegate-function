# create env variable aliases for the containers running our services, if we have docker available
if which docker >/dev/null && docker container ls > /dev/null; then
    CONTAINER_ALIASES=$(docker container ls |perl -ne 'if (/ (slurm-stack_([^\.]*)-srv\.\S*)/) { print("export $2=$1\n");}')
    eval $CONTAINER_ALIASES
fi
