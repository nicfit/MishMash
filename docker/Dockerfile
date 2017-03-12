FROM greyltc/archlinux
MAINTAINER Travis Shirk <travis@pobox.com>

EXPOSE 6229

RUN curl -o /etc/pacman.d/mirrorlist \
            "https://www.archlinux.org/mirrorlist/?country=US&protocol=https&use_mirror_status=on" && \
    sed -i 's/^#//' /etc/pacman.d/mirrorlist
RUN pacman -Syu --noconfirm
RUN pacman -S --noconfirm python python-virtualenv python-pip \
                          postgresql-libs python-psycopg2 git

ENV HOME=/home/mishmash \
    APP_DIR=/MishMash

# Default is SQLite but can be overridden.
ARG MISHMASH_DBURL=sqlite:////${APP_DIR}/var/MishMash.db
ENV MISHMASH_DBURL=${MISHMASH_DBURL} \
    MISHMASH_CONFIG=${APP_DIR}/etc/config.ini

RUN useradd -m mishmash -d ${HOME}
RUN echo "source ${APP_DIR}/bin/activate" >> ${HOME}/.bashrc && \
    echo "alias ll='ls -l'" >> ${HOME}/.bashrc

RUN mkdir -p ${APP_DIR} && chown mishmash:mishmash ${APP_DIR}
WORKDIR $APP_DIR
CMD ["/MishMash/bin/mishmash-init"]

USER mishmash
ENV LANG en_US.UTF-8

RUN mkdir -p ${APP_DIR}/etc ${APP_DIR}/var/log && \
    virtualenv --system-site-packages ${APP_DIR}

RUN source ${APP_DIR}/bin/activate && \
    pip install git+https://github.com/nicfit/MishMash.git
#RUN source ${APP_DIR}/bin/activate && \
#    pip install MishMash[postgres]

COPY mishmash-init ${APP_DIR}/bin/
COPY config.ini config-dev.ini ${APP_DIR}/etc/
#CMD ["/bin/bash"]
