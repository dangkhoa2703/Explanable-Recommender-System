# Use Python base image
FROM python:3.12.10-bookworm

# Set working directory
WORKDIR /app

# Copy only requirements first
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# # Then copy the rest of the app
# COPY . .

# Expose Streamlit's default port
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# # Add custom entrypoint script
# COPY start.sh /start.sh
# RUN chmod +x /start.sh

# ENTRYPOINT ["/start.sh"]

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]


