# **App Service - DeployForce**

## **📌 Overview**
The **App Service** is a Django-based microservice that provides the **frontend and backend API** for the DeployForce web application. It allows users to upload satellite images, interact with AI-generated damage segmentation, and generate disaster assessment reports.

## **📦 Features**
- 🚀 **User-friendly Web Interface** for image uploads & segmentation visualization.
- 🖼️ **Image Processing** with pre- and post-disaster image comparisons.
- 📊 **Damage Assessment Reports** with CSV/GeoJSON export.
- 🌎 **Interactive Map Integration** using Leaflet.js.
- 🔗 **REST API** for handling user requests and communication with the inference service.
- 📡 **Scalable Microservices Architecture** integrated with MLOps.

## **🛠️ Tech Stack**
- **Backend:** Django, Django REST Framework (DRF)
- **Frontend:** HTML, CSS, JavaScript, Leaflet.js
- **Database:** PostgreSQL/PostGIS (for geospatial data)
- **API Communication:** REST APIs
- **Deployment:** Docker, Kubernetes (Optional), AWS/GCP/Azure
- **Version Control:** Git, GitHub

## **⚙️ Installation**

### **🔹 Prerequisites**
Ensure you have the following installed:
- Python 3.9+
- Pipenv
- Supabase
- Docker (for containerized deployment)

### **🔹 Clone the Repository**
```bash
cd path/to/your/project

# Clone your repository
git clone https://github.com/your-username/your-repository.git
cd app_service
```

### **🔹 Install Dependencies**
```bash
pipenv install --dev
```

### **🔹 Setup Environment Variables**
Create a `.env` file inside `app_service/` and define environment variables:
```ini
DEBUG=True
SECRET_KEY=your_secret_key
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgres://user:password@db_host:5432/app_db
INFERENCE_API_URL=http://inference_service:8001/api/predict/
```

### **🔹 Apply Migrations & Run Server**
```bash
pipenv shell  # Activate virtual environment
python manage.py migrate
python manage.py runserver 8000
```

## **📡 API Endpoints**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload/` | POST | Upload satellite images |
| `/get-prediction/` | GET | Fetch AI-generated damage segmentation |
| `/generate-report/` | GET | Generate disaster damage reports |

## **🚀 Running with Docker**
Build and run the service using Docker:
```bash
docker build -t app_service .
docker run -p 8000:8000 --env-file .env app_service
```

## **🌍 Deployment**
For cloud deployment (AWS/GCP/Azure), use Docker & Kubernetes:
```bash
docker-compose up --build
```

## **📜 License**
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## **🤝 Contributing**
Contributions are welcome! Please fork the repo and submit a pull request.

## **📩 Contact**
For questions or support, contact [your-email@example.com](mailto:your-email@example.com).

