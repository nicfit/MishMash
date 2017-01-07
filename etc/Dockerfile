FROM greyltc/archlinux

RUN pacman -Syu --noconfirm
RUN pacman -S --noconfirm python python-pip git postgresql gcc
RUN git clone https://github.com/nicfit/mishmash.git /opt/MishMash
RUN pip install -r /opt/MishMash/requirements/default.txt
RUN cd /opt/MishMash && python setup.py install
