FROM ubuntu:20.04

ENV LANG zh_CN.UTF-8
ENV LANGUAGE zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8
ENV TZ Asia/Shanghai
ENV DEBIAN_FRONTEND noninteractive

ENV PIP_MIRROR="-i https://mirrors.ustc.edu.cn/pypi/web/simple"

RUN sed -i -e 's/archive\.ubuntu/mirrors\.163/' /etc/apt/sources.list

RUN apt-get update && apt-get install -y locales locales-all fonts-noto

RUN apt-get install -y python3 python3-pip

RUN pip install nb-cli $PIP_MIRROR
RUN pip install nonebot2 $PIP_MIRROR
RUN pip install nonebot-adapter-onebot $PIP_MIRROR
RUN pip install redis deep_translator pillow $PIP_MIRROR
RUN pip install pysocks $PIP_MIRROR
