FROM python:3.12-slim-bookworm

WORKDIR /home/pyuser/code

# Copy wheel into the container
COPY Chassis/dist/microservice_chassis-0.3.0-py3-none-any.whl ./Chassis/dist/

# Copy requirements
COPY Machine/machine_app/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -u 1000 -m pyuser && \
    chown -R pyuser:pyuser /home/pyuser

# Copy entrypoint and app
COPY Machine/machine_app/entrypoint.sh .
RUN chmod +x entrypoint.sh
COPY Machine/machine_app/app ./app

# Switch to non-root user
USER pyuser

ENTRYPOINT ["./entrypoint.sh"]
