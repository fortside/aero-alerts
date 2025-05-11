#based on https://wbarillon.medium.com/docker-python-image-with-psycopg2-installed-c10afa228016

# Build stage
FROM python:3.13.3-alpine AS builder
# Install system dependencies
RUN apk update && \
    apk add musl-dev libpq-dev gcc
#Create the virtual environment
RUN python -m venv /opt/venv
# Activate virtual environment
ENV PATH="/opt/venv/bin:$PATH"
COPY min-req.txt .
RUN pip install -r min-req.txt

# Operational stage
FROM python:3.13.3-alpine
#update and dependencies
RUN apk update && \
    apk add libpq-dev

#Copy the virtual env from the builder stage image
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

VOLUME /data

WORKDIR /app
COPY flight.py .
COPY registration.py .
COPY main.py .
COPY constants.py .
COPY helper_functions.py .
COPY config.py .

CMD ["python", "main.py"]
