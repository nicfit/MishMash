FROM mishmash-arch
MAINTAINER Travis Shirk <travis@pobox.com>

RUN pacman -S --noconfirm python-psycopg2
RUN pip install MishMash[postgres]
RUN chown -R $USER:$USER $MM_HOME

# user root above ^^^^
# -------------------------
# user mishmash below vvvv

USER $USER
ENV LANG en_US.UTF-8
CMD ["/MishMash/bin/mishmash-init"]

COPY config.ini ${MM_HOME}/etc/
# TODO: eyeD3 should be at error log level
COPY mishmash-init ${MM_HOME}/bin/
