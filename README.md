# 🚀 Yelp Camp Web Application - DevSecOps CI/CD Project

| Jenkins Pipeline | SonarQube Dashboard |
|-----------------|--------------------|
| ![](images/Screenshot_2026-06-08_123346.png) | ![](images/Screenshot_2026-06-08_123630.png) |

| Trivy Security Scan |
|---------------------|
| ![](images/Screenshot_2026-06-08_124626.png) |

---

## 📌 Project Overview

This web application allows users to add, view, access, and rate campgrounds by location. It is based on "The Web Developer Bootcamp" by Colt Steele, with additional enhancements, bug fixes, and a complete DevSecOps CI/CD implementation.

### Technologies Used

- **Node.js with Express** – Backend web server
- **Bootstrap** – Frontend UI design
- **Mapbox** – Interactive maps and location services
- **MongoDB Atlas** – Cloud database
- **Passport.js** – Authentication and authorization
- **Cloudinary** – Cloud image storage
- **Helmet** – Security hardening
- **Docker** – Containerization
- **Jenkins** – CI/CD automation
- **SonarQube** – Code quality analysis
- **Trivy** – Security vulnerability scanning
- **Slack** – Build notifications

---

## ⚙️ Setup Instructions

Create a `.env` file in the project root directory:

```sh
CLOUDINARY_CLOUD_NAME=[Your Cloudinary Cloud Name]
CLOUDINARY_KEY=[Your Cloudinary Key]
CLOUDINARY_SECRET=[Your Cloudinary Secret]
MAPBOX_TOKEN=[Your Mapbox Token]
DB_URL=[Your MongoDB Atlas Connection URL]
SECRET=[Your Secret Key]
```

Start the application:

```sh
docker compose up
```

---

## 🚀 CI/CD Pipeline Flow

1. Source Code Checkout
2. Dependency Installation
3. Automated Testing
4. Trivy Filesystem Scan
5. SonarQube Analysis
6. Docker Image Build
7. Trivy Image Scan
8. Docker Push
9. Docker Deployment
10. Slack Notification

---

## 🔒 Security Features

- SonarQube Static Code Analysis
- Trivy Filesystem Vulnerability Scan
- Trivy Docker Image Scan
- Helmet Security Headers
- Secure Environment Variables

---

## 👨‍💻 Author

**Prajwal B**

DevOps | Kubernetes | Cloud | CI/CD | DevSecOps
