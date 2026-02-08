# ################################################################################
# builder

FROM python:3.12-slim AS builder
ENV PYTHONUNBUFFERED 1

RUN apt-get update && \
    apt-get install -y gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv/
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /poor-man-toolbox/

COPY requirements.txt .

RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir --upgrade --requirement requirements.txt

COPY app/ app/


# ################################################################################
# final

FROM python:3.12-slim AS final

RUN apt-get update && \
    apt-get install -y curl chromium chromium-driver && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /poor-man-toolbox/

COPY --from=builder /poor-man-toolbox/ /poor-man-toolbox/
COPY --from=builder /opt/venv/ /opt/venv/

RUN groupadd -r poor && \
    useradd -m -r -g poor poor
RUN chown -R poor:poor /poor-man-dns/

USER poor

ENV PATH="/opt/venv/bin:$PATH"

# HEALTHCHECK CMD curl -fks https://localhost:5050/ || exit 1

# EXPOSE 53 583 5050 5053

STOPSIGNAL SIGINT

# CMD [ "python",  "-uX", "dev", "app/main.py" ]
# ENTRYPOINT ["python3", "login_and_export_cookies.py"]
