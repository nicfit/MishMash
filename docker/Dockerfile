FROM greyltc/archlinux
MAINTAINER Travis Shirk <travis@pobox.com>

EXPOSE 6229

RUN curl -o /etc/pacman.d/mirrorlist \
            "https://www.archlinux.org/mirrorlist/?country=US&protocol=https&use_mirror_status=on" && \
    sed -i 's/^#//' /etc/pacman.d/mirrorlist

RUN pacman -Syu --noconfirm
RUN pacman -S --noconfirm python python-pip git \
                          postgresql-libs python-psycopg2

RUN pip install git+https://github.com/nicfit/MishMash.git
RUN pip install MishMash[web]
RUN pip install MishMash[postgres]

ENV HOME=/home/mishmash \
    APP_DIR=/MishMash \
    LANG=en_US.UTF-8
ENV PATH="${APP_DIR}:${PATH}"

# Default is SQLite but can be overridden.
ARG MISHMASH_DBURL=sqlite:////${APP_DIR}/var/MishMash.db
ENV MISHMASH_DBURL=${MISHMASH_DBURL} \
    MISHMASH_CONFIG=${APP_DIR}/etc/config.ini

RUN useradd -m -d ${HOME} --uid 6229 mishmash

RUN mkdir -p ${APP_DIR}/bin ${APP_DIR}/etc ${APP_DIR}/var && \
    chown mishmash:mishmash ${APP_DIR} ${APP_DIR}/var
WORKDIR $APP_DIR

USER mishmash
CMD ["/MishMash/bin/mishmash-init"]

COPY mishmash-init ${APP_DIR}/bin/
COPY config.ini config-dev.ini ${APP_DIR}/etc/
