FROM python:3.7-alpine
MAINTAINER Travis Shirk <travis@pobox.com>
EXPOSE 6229
ENV HOME=/home/mishmash \
    APP_DIR=/MishMash \
    LANG=en_US.UTF-8

ARG VERSION

RUN apk update &&\
    apk upgrade &&\
    python -m venv ${APP_DIR} &&\
    addgroup -S mishmash &&\
    adduser -S -u 6229 -G mishmash -h ${HOME} mishmash

RUN source ${APP_DIR}/bin/activate &&\
    pip --no-cache-dir install -U pip &&\
    apk add --no-cache libmagic postgresql-libs &&\
    apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev &&\
    pip --no-cache-dir install MishMash[web]==${VERSION} &&\
    pip --no-cache-dir install MishMash[postgres]==${VERSION} &&\
    apk --purge del .build-deps

RUN mkdir -p ${APP_DIR}/etc ${APP_DIR}/var &&\
    chown -R mishmash:mishmash ${APP_DIR}

USER mishmash
ENV PATH="${APP_DIR}/bin:${PATH}"
ENTRYPOINT ["mishmash"]
