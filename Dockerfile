# The base image
FROM python:3.10.0-slim-bullseye

# Install python and pip

# Install Python modules needed by the Python app
RUN pip3 install kafka-python==2.0.2 requests --no-cache-dir

# Copy files required for the app to run
COPY dlr_import_amps.py ksql-config.json /DLR/

# Declare the port number the container should expose

# Run the application
CMD ["python3", "/DLR/dlr_import_amps.py"]