<div align="center">

# 🏪 MyDuka

### Inventory Management System for Kenyan Businesses

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-Frontend-2563EB?style=for-the-badge)](https://myduka-frontend.onrender.com)
[![Backend API](https://img.shields.io/badge/⚙️_Backend_API-Live-059669?style=for-the-badge)](https://myduka-backend-9m1l.onrender.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-d4a853?style=for-the-badge)](LICENSE)

---

**MyDuka** is a full-stack, multi-tenant inventory management SaaS built for Kenyan merchants and store owners.
It enables real-time stock tracking, insightful reporting, supply chain management, and role-based access control — all from one sleek dashboard.

</div>

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [🏗️ Architecture](#️-architecture)
- [📁 Project Structure](#-project-structure)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Database Setup](#database-setup)
- [🔌 API Reference](#-api-reference)
- [👥 User Roles](#-user-roles)
- [📸 Screenshots](#-screenshots)
- [🔮 Roadmap](#-roadmap)
- [👨‍💻 Authors](#-authors)
- [📄 License](#-license)

---

## ✨ Features

### 🔐 Role-Based Authentication
- **Merchants** (Superusers) invite Admins via secure tokenized email links
- **Admins** manage clerks, approve supply requests, and oversee store operations
- **Clerks** record stock entries, submit supply requests, and monitor alerts
- JWT-based auth with refresh tokens and invitation-based registration flow

### 📦 Inventory Management
- Record stock entries with quantity, buying/selling price, payment status, and spoilage
- Track products across multiple store branches simultaneously
- Real-time low stock alerts with automated threshold detection
- Full spoilage rate tracking and analysis

### 🔄 Supply Chain Requests
- Clerks submit stock replenishment requests directly from the dashboard
- Admins approve or decline with reason — clerks notified in real-time via WebSocket
- Full request history with status tracking (Pending / Approved / Declined)

### 📊 Reports & Analytics
- Weekly and monthly performance reports
- Visual bar and line charts (Chart.js) for sales trends and top products
- Per-store, per-clerk, and per-product breakdown
- One-click PDF export for reports

### 🏢 Multi-Store Management
- Merchants manage multiple store locations from a single dashboard
- Assign admins and clerks to specific stores
- Cross-store analytics and comparison

### ⚡ Real-Time Updates
- Socket.IO powers live notifications for supply requests, stock alerts, and payment updates
- Live dashboard metrics that refresh without page reload

---

## 🛠️ Tech Stack

<table>
<tr>
<td valign="top" width="33%">

### Backend
- **Python 3.11+** / Flask
- Flask-JWT-Extended
- Flask-SQLAlchemy
- Flask-SocketIO (gevent)
- Flask-Mail
- Flask-CORS
- Flask-Limiter
- Flask-Caching
- Marshmallow
- Python-dotenv

</td>
<td valign="top" width="33%">

### Frontend
- **React.js** + Vite
- Redux Toolkit
- Axios
- Chart.js / react-chartjs-2
- Socket.IO Client
- React Router v6
- jsPDF
- Lodash

</td>
<td valign="top" width="33%">

### Infrastructure
- **PostgreSQL** (Database)
- **Render** (Hosting)
- Redis (optional caching)
- Flask-Migrate (migrations)

</td>
</tr>
</table>

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────┐
│                   CLIENT (React)                  │
│  Merchant  │  Admin Portal  │  Clerk Portal       │
│  Dashboard │                │                     │
└─────────────────────┬────────────────────────────┘
                      │  REST API + WebSocket
┌─────────────────────▼────────────────────────────┐
│               SERVER (Flask)                      │
│  Auth  │  Inventory  │  Reports  │  Notifications │
│  Users │  Stores     │  Dashboard│  Socket.IO     │
└─────────────────────┬────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────┐
│              DATABASE (PostgreSQL)                │
│  Users │ Stores │ Products │ Inventory Entries    │
│  Supply Requests │ Sales Records │ Notifications  │
└──────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
MyDuka/
├── server/                         # Flask Backend
│   ├── routes/                     # API blueprints
│   │   ├── auth.py                 # Authentication routes
│   │   ├── users.py                # User management
│   │   ├── inventory.py            # Stock & supply routes
│   │   ├── reports.py              # Analytics routes
│   │   ├── dashboard.py            # Dashboard summary
│   │   ├── stores.py               # Store management
│   │   └── notifications.py        # Notification routes
│   ├── sockets/                    # Socket.IO event handlers
│   ├── tests/                      # Unit & integration tests
│   ├── app.py                      # App entry point
│   ├── config.py                   # Environment configuration
│   ├── extensions.py               # Flask extensions
│   ├── models.py                   # SQLAlchemy models
│   ├── schemas.py                  # Marshmallow schemas
│   ├── seed.py                     # Database seeder
│   ├── .env                        # Environment variables
│   └── requirements.txt            # Python dependencies
│
└── client/                         # React Frontend
    ├── src/
    │   ├── Components/
    │   │   ├── Admin/              # Admin dashboard pages
    │   │   ├── Clerk/              # Clerk dashboard pages
    │   │   ├── Merchant/           # Merchant dashboard pages
    │   │   ├── NavBar/             # Shared navigation
    │   │   ├── Footer/             # Shared footer
    │   │   ├── LoginPage/          # Authentication pages
    │   │   ├── Routes/             # Protected route guards
    │   │   └── Notifications/      # Real-time notifications
    │   ├── context/
    │   │   └── AuthContext.jsx     # Authentication context
    │   ├── hooks/
    │   │   └── useSocket.js        # Socket.IO hook
    │   ├── store/
    │   │   └── slices/             # Redux state slices
    │   ├── utils/
    │   │   ├── api.js              # Axios instance & helpers
    │   │   └── formatters.js       # Currency & date formatters
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |
| Git | Latest |

---

### Backend Setup

**1. Clone the repository**
```bash
git clone https://github.com/your-username/myduka.git
cd myduka
```

**2. Set up a virtual environment**
```bash
cd server
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file inside the `server/` directory:
```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/myduka

# Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key

# Email (Mailtrap for dev, or real SMTP for production)
MAIL_SERVER=smtp.mailtrap.io
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-mailtrap-username
MAIL_PASSWORD=your-mailtrap-password
MAIL_DEFAULT_SENDER=noreply@myduka.com

# Optional: Redis cache
REDIS_URL=redis://localhost:6379/0
```

**5. Start the backend server**
```bash
python app.py
```
> Backend runs at `http://localhost:5000`

---

### Frontend Setup

**1. Navigate to the client directory**
```bash
cd ../client
npm install
```

**2. Configure environment variables**

Create a `.env` file inside the `client/` directory:
```env
VITE_API_BASE_URL=http://localhost:5000
```

**3. Start the development server**
```bash
npm run dev
```
> Frontend runs at `http://localhost:3000`

---

### Database Setup

**1. Create the database**
```bash
psql -U your_username -c "CREATE DATABASE myduka;"
```

**2. Run migrations**
```bash
cd server
flask db upgrade
```

**3. Seed with sample data**
```bash
python seed.py
```

**Seed creates:**
- 1 Merchant account
- 3 Store locations
- 5 Admin accounts
- 10 Clerk accounts
- Sample products and inventory entries

> **Default Login (Merchant):** Check seed.py output for credentials

---

## 🔌 API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Login and receive access + refresh tokens |
| `POST` | `/api/auth/register` | Register via invite token |
| `POST` | `/api/auth/invite` | Send invitation email (Merchant/Admin only) |
| `POST` | `/api/auth/refresh` | Refresh access token |
| `GET` | `/api/auth/google/login` | Google OAuth login |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users/admins` | List all admins (Merchant only) |
| `GET` | `/api/users/clerks` | List all clerks (Admin only) |
| `PUT` | `/api/users/:id` | Update user details |
| `PUT` | `/api/users/:id/status` | Activate or deactivate a user |
| `DELETE` | `/api/users/:id` | Delete a user |

### Inventory

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/inventory/products` | List all products |
| `POST` | `/api/inventory/entries` | Add a new stock entry |
| `GET` | `/api/inventory/entries` | List all stock entries |
| `GET` | `/api/inventory/low-stock` | Get low stock alerts |
| `POST` | `/api/inventory/supply-requests` | Create a supply request |
| `GET` | `/api/inventory/supply-requests` | List supply requests |
| `PUT` | `/api/inventory/supply-requests/:id/approve` | Approve a request |
| `PUT` | `/api/inventory/supply-requests/:id/decline` | Decline a request |
| `GET` | `/api/inventory/suppliers/paid` | List paid supplier entries |
| `GET` | `/api/inventory/suppliers/unpaid` | List unpaid supplier entries |
| `PUT` | `/api/inventory/update-payment/:id` | Mark payment as paid |

### Reports & Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/dashboard/summary` | Dashboard summary metrics |
| `GET` | `/api/reports/sales` | Sales report (weekly/monthly) |
| `GET` | `/api/reports/top-products` | Top selling products |
| `GET` | `/api/stores` | List all stores |

> All protected endpoints require `Authorization: Bearer <token>` header.

---

## 👥 User Roles

```
MERCHANT (Superuser)
├── Invite & manage Admins
├── View cross-store reports & analytics
├── Track supplier payments (all stores)
└── Access full dashboard metrics

    ADMIN (Store Manager)
    ├── Invite & manage Clerks
    ├── Approve / decline supply requests
    ├── View inventory overview
    ├── Track store-level payments
    └── Access store reports

        CLERK (Ground Level)
        ├── Submit stock entries
        ├── Raise supply requests
        ├── View low stock alerts
        └── View own activity log
```

---

## 🔮 Roadmap

- [ ] Email notifications for supply request approvals / declines
- [ ] OTP-based password reset flow
- [ ] Multi-period chart comparisons (e.g., month-over-month)
- [ ] Full audit logs with activity timeline
- [ ] Mobile-responsive PWA support
- [ ] Barcode scanner integration for stock entry
- [ ] Bulk CSV/Excel import for products
- [ ] WhatsApp / SMS alerts for low stock

---

## 👨‍💻 Authors

Built with ❤️ by the MyDuka team:

| Name | Email |
|------|-------|
| Edith Gatwiri | edithgatwiri70@gmail.com |
| Elly James | ellykomunga@gmail.com |
| Helen Wairagu | hwangari3@gmail.com |
| Ian Gathua | gathuambui@gmail.com |
| Edwin Ngigi | edwinngigi313@gmail.com |

For any support or issues, reach out via the emails above or open a GitHub issue.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Made in Kenya 🇰🇪 &nbsp;|&nbsp; © 2026 MyDuka

[![Frontend](https://img.shields.io/badge/🌐_Frontend-myduka--frontend.onrender.com-2563EB?style=flat-square)](https://myduka-frontend.onrender.com)
[![Backend](https://img.shields.io/badge/⚙️_API-myduka--backend--9m1l.onrender.com-059669?style=flat-square)](https://myduka-backend-9m1l.onrender.com)

</div>