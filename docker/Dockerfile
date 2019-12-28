FROM python:3.8-alpine
MAINTAINER Travis Shirk <travis@pobox.com>
EXPOSE 6229
ENTRYPOINT ["mishmash"]

ARG VERSION
ENV HOME=/home/mishmash \
    LANG=en_US.UTF-8

RUN apk update &&\
    apk upgrade &&\
    python -m ensurepip &&\
    pip --no-cache-dir install -U pip setuptools &&\
    apk add --no-cache ca-certificates libmagic postgresql-libs

# Deps requiring extra build tools to be clean up after
RUN apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev &&\
    pip --no-cache-dir install psycopg2-binary \
                               gevent gunicorn &&\
    apk --purge del .build-deps

RUN addgroup -S mishmash &&\
    adduser -S -u 6229 -G mishmash -h ${HOME} mishmash &&\
    mkdir -p ${HOME}/etc ${HOME}/var ${HOME}/bin

RUN pip --no-cache-dir install MishMash[web]==${VERSION}

USER mishmash
ENV PATH="${HOME}/bin:${PATH}"
RUN find ${HOME}
