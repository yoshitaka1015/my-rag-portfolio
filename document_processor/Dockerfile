# Use the official Python base image.
FROM python:3.11-slim

# Install Tesseract OCR and its dependencies, and poppler for PDF handling
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set the entrypoint for the function
CMD exec functions-framework --target=process_document