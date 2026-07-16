FROM --platform=linux/amd64 ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    WINEARCH=win64 \
    WINEPREFIX=/opt/wineprefix \
    DISPLAY=:99 \
    PYTHON_VERSION=3.12.10

RUN dpkg --add-architecture i386 && apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl xvfb wine wine64 wine32 unzip p7zip-full cabextract && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/downloads && \
    curl -fsSL "https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-amd64.exe" \
      -o /opt/downloads/python.exe && \
    curl -fsSL "https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe" \
      -o /opt/downloads/innosetup.exe && \
    xvfb-run -a wineboot -u && \
    xvfb-run -a wine /opt/downloads/python.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 TargetDir=C:\\Python312 && \
    xvfb-run -a wine /opt/downloads/innosetup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- && \
    xvfb-run -a wine C:\\Python312\\python.exe -m pip install --upgrade pip

WORKDIR /workspace
COPY packaging/windows/build_with_wine.sh /usr/local/bin/build-with-wine
RUN chmod +x /usr/local/bin/build-with-wine

ENTRYPOINT ["/usr/local/bin/build-with-wine"]
