# ⚡ Electric Vehicle (EV) Charging Station Management System

A smart, centralized digital platform for managing and accessing EV charging stations — built to solve real-time monitoring, slot allocation, and booking inefficiencies in traditional charging systems.

### 🔗 [Live Demo](https://electric-vc-app.vercel.app/)

## 📌 Overview

With the rapid growth of Electric Vehicles (EVs), the demand for efficient and reliable charging infrastructure has increased significantly. Traditional charging station management systems often lack real-time monitoring, optimized slot allocation, and seamless interaction between users and service providers — leading to long waiting times and poor resource utilization.

This project introduces an **EV Charging Station Management System**, an integrated platform that connects administrators and users through a structured, technology-driven approach — enabling real-time tracking, efficient coordination, and a better overall charging experience.

## 🚀 Key Features

- **Modular Architecture** — Built around two core modules: Admin and User
- **Real-Time Monitoring** — Live tracking of station status and slot availability
- **Location-Based Services** — Google Maps integration to locate nearby charging stations
- **Controlled Booking Workflow** — Prevents overbooking and slot conflicts, with row-level locking to safely handle multiple users booking at once
- **Booking History & Usage Tracking** — Users can view their past charging sessions
- **Centralized Admin Control** — Station creation, slot management, and booking verification
- **Cloud-Hosted Profile Pictures** — Instagram-style user profiles with images stored on Cloudinary

## 🧩 System Modules

### 🔹 Admin Module
- Create and manage charging stations
- Allocate and update charging slots
- Verify and approve booking requests
- Centralized monitoring of all stations

### 🔹 User Module
- Locate nearby charging stations via interactive map
- Submit charging slot booking requests
- Track charging history and usage
- Simple, user-friendly interface

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML, CSS, Bootstrap |
| **Backend** | Python (Flask) |
| **Database** | PostgreSQL (hosted on Neon) |
| **Image Storage** | Cloudinary |
| **Maps / Geolocation** | Google Maps API |
| **Deployment** | Vercel (serverless) |
| **Other Libraries** | Flask-SQLAlchemy, Flask-Login, Jinja2, Werkzeug |

## 🏗️ System Architecture

The platform follows a modular design comprising the Admin Module and User Module, integrated with real-time data management and geolocation services to ensure smooth coordination between service providers and users. The Flask backend handles routing, authentication, and business logic, while a hosted PostgreSQL database (Neon) manages persistent, concurrent-safe data storage — allowing multiple users to book and manage slots at the same time without conflicts. Profile pictures are uploaded directly to Cloudinary rather than local storage, keeping the app fully compatible with serverless deployment on Vercel. The frontend, built with Bootstrap, delivers a clean and responsive interface across devices.

## 🔑 Demo Credentials

Use the following credentials to explore the application:

```
Admin Login
Email    : admin@gmail.com
Password : admin123

User Login
Email    : user@evcharge.com
Password : user123
```

> ⚠️ These are demo credentials for testing purposes only.

## 🎯 Objective

To build a scalable and intelligent EV charging infrastructure that:
- Reduces waiting time and booking conflicts
- Improves resource utilization
- Enhances transparency between admins and users
- Supports the broader vision of sustainable mobility and smart city ecosystems

## 📈 Future Scope

- Payment gateway integration
- AI-based slot prediction and demand forecasting
- Real-time notifications for booking status
- Analytics dashboard for admins

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](../../issues).

## 📧 Contact

For queries or suggestions, feel free to reach out.

---

⭐ If you find this project useful, don't forget to give it a star!
