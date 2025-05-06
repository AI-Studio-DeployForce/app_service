FROM python:3.9
WORKDIR /app
COPY Pipfile Pipfile.lock ./
RUN pip install pipenv && pipenv install --deploy --ignore-pipfile
COPY . .
CMD ["pipenv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]