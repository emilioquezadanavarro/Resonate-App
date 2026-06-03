# Use the official Python image as a base ( minimal version )
FROM python:3.13-slim

# Set the working directory inside the container 
WORKDIR /app

# Copy requirements into the container 
COPY requirements.txt .

# Install dependencies ( no cache dir to avoid caching the dependencies )
RUN pip install --no-cache-dir -r requirements.txt

# Copy other files into the container
COPY . .

# Tells wich port the app is using
EXPOSE 5000

# Run the application
CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:5000"] 