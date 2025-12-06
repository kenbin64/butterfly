# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables
# These can be overridden at runtime (e.g., with docker run -e)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BUTTERFLY_EDITION="COMMUNITY"
ENV JWT_SECRET_KEY="default-super-secret-key-for-dev"
# BUTTERFLY_ENCRYPTION_KEY should be provided at runtime for security.

# Create a non-root user and group
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code
COPY . .

# Change ownership of the app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Expose the port the app runs on
EXPOSE 5001

# Add a health check to verify the service is operational
# It waits 15s before the first check, then checks every 60s.
# It retries 3 times before marking the container as unhealthy.
HEALTHCHECK --interval=60s --timeout=15s --start-period=15s --retries=3 \
  CMD python health_check.py || exit 1

# Command to run the application using Gunicorn
# The 'app:butterfly_helper' needs to be initialized before gunicorn starts.
# We run app.py with a special argument to initialize and then gunicorn takes over.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "app:app"]