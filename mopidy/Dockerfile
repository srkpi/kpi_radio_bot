FROM ubuntu

ENV TZ "Etc/UTC"

RUN export DEBIAN_FRONTEND=noninteractive  \
    && apt update  \
    && apt install -y wget gnupg2 gstreamer1.0-libav pulseaudio python3-pip \
    && mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/mopidy-archive-keyring.gpg https://apt.mopidy.com/mopidy.gpg \
    && wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/bookworm.list \
    && apt update  \
    && apt install -y mopidy \
    && python3 -m pip install Mopidy-Mobile --break-system-packages \
    && python3 -m pip cache purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* ~/.cache


RUN adduser myuser && chown myuser /home/myuser
COPY pulse-client.conf /etc/pulse/client.conf
COPY mopidy.conf /home/myuser/.config/mopidy/mopidy.conf
EXPOSE 6680
USER myuser
CMD ["mopidy"]
