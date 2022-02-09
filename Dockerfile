# The base image
FROM python:3.10.0-slim-bullseye

# Install Python modules needed by the Python app
COPY app/requirements.txt /
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt --no-cache-dir && rm requirements.txt

# Copy files required for the app to run
COPY app/* /app/

# Declare the port number the container should expose

# Run the application
CMD ["python3", "-u", "/app/dlr_import_amps.py"]
