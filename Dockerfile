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
