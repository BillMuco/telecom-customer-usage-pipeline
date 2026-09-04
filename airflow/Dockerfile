FROM apache/airflow:2.10.5-python3.11

# Spark 3.5.8 requires a Java runtime. Install it as root, then restore the
# non-privileged Airflow user for all subsequent image operations.
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
USER airflow

# Install the Spark provider while retaining the Airflow version from the base image.
RUN python -m pip install --no-cache-dir \
    --constraint https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.11.txt \
    apache-airflow==2.10.5 \
    apache-airflow-providers-apache-spark==5.0.0

# The Airflow executable is installed in the image user's local bin directory.
ENV PATH="/home/airflow/.local/bin:${PATH}"

# Fail the image build if the CLI is not present.
RUN command -v airflow && airflow version

# Match the Spark runtime UID while retaining Airflow's named account.
USER root
RUN usermod --uid 185 airflow \
    && chown -R 185:0 /home/airflow /opt/airflow
USER airflow
