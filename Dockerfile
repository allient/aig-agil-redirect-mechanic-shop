# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install Poetry
RUN apt clean && apt update && apt install curl -y
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

# Copy the current directory contents into the container at /app
COPY . /app

# Allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
RUN poetry install --no-root --no-dev

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Define environment variable
ENV STREAMLIT_SERVER_PORT=8501

# Run streamlit when the container launches
CMD ["streamlit", "run", "--server.port", "8501", "frontend/app.py"]
