#base image
FROM python:3.12-slim

# set work directory
WORKDIR /app

COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

COPY . .

# run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
