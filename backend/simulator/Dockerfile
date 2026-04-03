FROM python:3.12-slim

WORKDIR /simulator

RUN pip install --no-cache-dir httpx
COPY service_simulator.py .

CMD ["python", "service_simulator.py"]
