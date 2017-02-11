FROM greyltc/archlinux
MAINTAINER Travis Shirk <travis@pobox.com>

RUN pacman -Syu --noconfirm
RUN pacman -S --noconfirm python python-pip python-virtualenv

ENV MM_HOME /MishMash
ENV USER mishmash
ENV HOME /home/$USER
ARG MISHMASH_DBURL=sqlite:////${MM_HOME}/var/MishMash.db
ENV MISHMASH_DBURL ${MISHMASH_DBURL}
ENV MISHMASH_CONFIG ${MM_HOME}/etc/config.ini

RUN pacman -S --noconfirm gcc git postgresql-libs vim

RUN useradd -m ${USER} -d ${HOME}
RUN echo "source ${MM_HOME}/bin/activate" >> ${HOME}/.bashrc && \
    echo "alias ll='ls -l'" >> ${HOME}/.bashrc

RUN mkdir $MM_HOME && chown $USER:$USER $MM_HOME

# ^^^ user root
# VVV user mishmash

USER $USER
RUN virtualenv $MM_HOME

RUN mkdir ${MM_HOME}/etc
RUN mkdir ${MM_HOME}/var

ENV RECLONE bjm
RUN git clone https://github.com/nicfit/mishmash.git ${MM_HOME}/src && true
RUN source ${MM_HOME}/bin/activate && \
    pip install -U pip && \
    pip install -r ${MM_HOME}/src/requirements.txt && \
    pip install -r ${MM_HOME}/src/requirements/test.txt && \
    pip install -r ${MM_HOME}/src/requirements/dev.txt && \
    cd ${MM_HOME}/src && python setup.py install

CMD ["/MishMash/bin/mishmash-init"]
#CMD ["/bin/bash"]

COPY config.ini ${MM_HOME}/etc/
COPY mishmash-init ${MM_HOME}/bin/

ENV LANG en_US.UTF-8
