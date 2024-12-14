FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    asymptote \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-luatex \
    texlive-pictures \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of your app
COPY . .

# Expose the port that Streamlit listens on
EXPOSE 8080

# Command to run the app
CMD ["streamlit", "run", "lyranmath-app.py", "--server.port=8080", "--server.address=0.0.0.0"]
