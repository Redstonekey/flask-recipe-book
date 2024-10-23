# Use the official Python image as the base image
FROM python:3.8

# Set the working directory in the container
WORKDIR /app

# Copy the application files into the working directory
COPY . /app

# Install the application dependencies
RUN pip install -r requirements.txt

# Ensure static files are served correctly
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_APP=main.py
ENV FLASK_ENV=production

# Expose the port Flask runs on
EXPOSE 5000

# Define the entry point for the container
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
<<<<<<< HEAD
# Use the official Python image as the base image
FROM python:3.8

# Set the working directory in the container
WORKDIR /app

# Copy the application files into the working directory
COPY . /app

# Install the application dependencies
RUN pip install -r requirements.txt

# Ensure static files are served correctly
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_APP=main.py
ENV FLASK_ENV=production

# Expose the port Flask runs on
EXPOSE 5000

# Define the entry point for the container
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
