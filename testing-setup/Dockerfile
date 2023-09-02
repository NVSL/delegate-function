FROM stevenjswanson/cse142l-swanson-dev:latest

LABEL org.opencontainers.image.source="https://github.com/NVSL/cfiddle-slurm" \
      org.opencontainers.image.title="cfiddle-slurm-cluster" \
      org.opencontainers.image.description="CFiddle + Slurm Docker cluster on Ubuntu" \
      org.label-schema.docker.cmd="docker-compose up -d" \
      maintainer="Steven Swanson"

USER root
RUN mkdir /slurm
WORKDIR /slurm


COPY testing-setup/SLURM_TAG ./
COPY testing-setup/IMAGE_TAG ./
COPY testing-setup/slurm.conf ./
COPY testing-setup/slurmdbd.conf ./

COPY testing-setup/install_slurm.sh ./
RUN  ./install_slurm.sh

RUN mkdir -p /build
COPY . /build/delegate-function/
RUN (cd /build/delegate-function; ls; /opt/conda/bin/python -m pip install .)

#RUN ls /opt/conda/lib/python3.10/site-packages/cfiddle*
#COPY ./install_cfiddle.sh ./
#RUN ./install_cfiddle.sh 

RUN groupadd cfiddlers
RUN groupadd --gid 1001 docker_users
RUN useradd -g cfiddlers -p fiddle -G docker_users -s /usr/bin/bash test_fiddler
RUN useradd -r -s /usr/sbin/nologin -u 7000 -G docker_users -p fiddle cfiddle 
COPY testing-setup/cfiddle_sudoers /etc/sudoers.d

RUN apt-get update --fix-missing
RUN apt-get install -y openssh-server acl && apt-get clean

COPY testing-setup/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN mkdir -p /scratch
RUN chmod a+rwx /scratch

ENTRYPOINT ["/opt/conda/bin/cfiddle_with_env.sh", "/usr/local/bin/docker-entrypoint.sh"]
CMD ["slurmdbd"]