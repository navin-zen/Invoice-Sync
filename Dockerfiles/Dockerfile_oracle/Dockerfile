FROM python:3.7.12-bullseye

ENV PYTHONBUFFERED=1

WORKDIR /gstzen

# Update and upgrade packages
RUN apt-get update -y && \
    apt-get upgrade -y

# Install necessary dependencies
RUN apt-get install -y build-essential python3-dev unixodbc-dev python3-venv wget tar git

# Download einvoicing-local-ui-latest.tar.gz and extract
RUN wget https://img-www.gstzen.in/pdfs/einvoicing-local-ui/einvoicing-local-ui-latest.tar.gz -O einvoicing-local-ui-latest.tar.gz && \
    tar -zxf einvoicing-local-ui-latest.tar.gz

# Navigate to the static directory and create necessary folders
WORKDIR /gstzen/projects/einvoicing-local-UI/config/static
RUN mkdir -p generated/javascript

# Navigate back to the project root
WORKDIR /gstzen/projects/einvoicing-local-UI

# Create necessary folders for static files
RUN mkdir -p .staticfiles/generated/javascript

# Navigate back to the project root
WORKDIR /gstzen

# Download bundle.js
RUN wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1qxu3A673788FfS67jShzCNTznEPZS_1n' -O projects/einvoicing-local-UI/config/static/generated/javascript/bundle.js && \
    wget --no-check-certificate 'https://docs.google.com/uc?export=download&id=1qxu3A673788FfS67jShzCNTznEPZS_1n' -O projects/einvoicing-local-UI/.staticfiles/generated/javascript/bundle.js

# Create Python virtual environment
RUN python3 -m venv projects/einvoicing-local-UI/.venv

# Install git
RUN apt-get install git -y

# Install Python dependencies
RUN projects/einvoicing-local-UI/activator pip install -r projects/einvoicing-local-UI/requirements.txt

# Reset the database
RUN cd projects/einvoicing-local-UI && bash reset_db.sh

# Install and configure Oracle Instant Client
RUN wget https://download.oracle.com/otn_software/linux/instantclient/211000/instantclient-basic-linux.x64-21.1.0.0.0.zip && \
    apt-get install unzip -y && \
    unzip instantclient-basic-linux.x64-21.1.0.0.0.zip && \
    apt-get install libaio1 -y

WORKDIR /gstzen/projects/einvoicing-local-UI/

# Create a shell script with the specified command
RUN echo "#!/bin/bash" > start_app.sh
RUN echo ".envs/.development services/rev-specific/keep-supervisor-alive >> start_app.sh
RUN echo "tail -f ./services/rev-specific/run_tasks/run_tasks.log" >> start_app.sh
RUN chmod +x start_app.sh

EXPOSE 9007

# Set the entrypoint script for container startup
ENTRYPOINT ["/gstzen/projects/einvoicing-local-UI/start_app.sh"]
CMD ["./start_app.sh"]
