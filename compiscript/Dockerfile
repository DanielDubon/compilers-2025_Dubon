FROM ubuntu:latest

# Esta parte no la necesitan realmente ustedes, pero igual, la voy a dejar comentada y lo escribo en español para su atención jaja
# Esencialmente esta parte sirve cuando están detrás de una proxy y necesitan especificar explícitamente
# los certificados para poderse conectar a internet con firmas de sus CAs.
# Es una configuración avanzada y no la necesitan realmente.

# # Set working directory
# WORKDIR /opt/certs

# # Update image and package lists
# RUN apt-get update \
#     && apt-get -y upgrade \
#     && apt-get clean

# USER root

# # Install common dependencies
# RUN apt-get update \
#     && apt-get -y install --no-install-recommends \
#     ca-certificates \
#     wget \
#     less \
#     tar 

# # Configure certificates
# COPY ../configs/certs/* /opt/certs
# RUN cp -a /opt/certs/* /usr/local/share/ca-certificates/
# RUN update-ca-certificates

# Install packages
FROM ubuntu:latest
ENV DEBIAN_FRONTEND=noninteractive

# Paquetes base + Java + Python con venv
RUN apt-get update && apt-get install -y \
    curl bash-completion openjdk-17-jdk fontconfig fonts-dejavu-core software-properties-common \
    graphviz \
    python3 python3-venv python3-pip ca-certificates git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ANTLR
COPY antlr-4.13.1-complete.jar /usr/local/lib/antlr-4.13.1-complete.jar
COPY ./commands/antlr /usr/local/bin/antlr
RUN chmod +x /usr/local/bin/antlr && ln -s /usr/local/bin/antlr /usr/bin/antlr
COPY ./commands/grun /usr/local/bin/grun
RUN chmod +x /usr/local/bin/grun && ln -s /usr/local/bin/grun /usr/bin/grun

# Virtualenv en /opt/venv y usarlo por defecto
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN python -m pip install -U pip setuptools wheel

# Dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Usuario sin privilegios
ARG USER=appuser
ARG UID=1001
RUN adduser --disabled-password --gecos "" --home "/home/${USER}" --uid "${UID}" "${USER}"
USER ${UID}

WORKDIR /program
