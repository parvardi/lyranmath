# FROM ubuntu:22.04

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     python3 \
#     python3-pip \
#     asymptote \
#     texlive-latex-recommended \
#     texlive-fonts-recommended \
#     texlive-luatex \
#     texlive-pictures \
#     && rm -rf /var/lib/apt/lists/*

# # Set the working directory
# WORKDIR /app

# # Copy requirements and install Python dependencies
# COPY requirements.txt .
# RUN pip3 install --no-cache-dir -r requirements.txt

# # Copy the rest of your app
# COPY . .

# # Expose the port that Streamlit listens on
# EXPOSE 8080

# # Command to run the app
# CMD ["streamlit", "run", "lyranmath-app.py", "--server.port=8080", "--server.address=0.0.0.0"]

# Use the official Python 3.11 slim image as the base
FROM python:3.11-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install system dependencies
RUN apt-get update && apt-get install -y \
    asymptote \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-luatex \
    texlive-pictures \
    && rm -rf /var/lib/apt/lists/*

# Verify Asymptote installation
RUN which asy && asy --version

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the image
COPY . .

# Expose the port Streamlit will run on
EXPOSE 8080

# Command to run your Streamlit app
CMD ["streamlit", "run", "lyranmath-app.py", "--server.port=8080", "--server.address=0.0.0.0"]
