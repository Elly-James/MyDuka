# MyDuka
- MyDuka is a full-stack inventory management system designed to streamline record-keeping and stock-taking for merchants and store owners. The application enables real-time tracking of inventory, generation of insightful reports, and controlled user access across roles such as Merchant, Admin, and Clerk.
- The backend is built using Python (Flask) and the frontend with React.js, providing a responsive and seamless experience for managing stores and supply chains.

## Table of Contents
    - MyDuka
    - Features
    - Technologies Used
    - Backend
    - Frontend
    - Database
    - Project Structure
    - Setup Instructions
    - Prerequisites
    - Backend Setup
    - Frontend Setup
    - Database Setup
    - API Endpoints
    - Authentication
    - Users
    - Reports
    - Inventory
    - Future Enhancements
    - Authors
    - License

## Features
### Role-Based Authentication
- Superusers (Merchants) initiate admin registration via tokenized email links.
- Admins manage clerks and stores.
- Clerks can manage inventory and request supplies.

### Inventory Management
- Add stock entries including quantity, payment status, spoilage, buying/selling price.
- Low stock alerts.
- Track products across multiple branches.

### Supply Chain Requests
- Clerks can request more stock.
- Admins approve or decline requests.

### Reports & Visualization
- Weekly and monthly reports.
- Visual insights through bar and line graphs.
- view reports per store, per clerk, and per product.

### Account Management

Deactivate/delete users (Admins/Clerks).

Role-based dashboard access and permission control.

## Technologies Used

### Backend
- Flask
- Flask-JWT-Extended
- Flask-SQLAlchemy
- Flask-Mail
- Flask-CORS
- Flask-SocketIO
- Marshmallow
- Python-dotenv

### Frontend

- React.js
- Axios
- Vite
- Chart.js 

### Database
PostgreSQL

#### Project Structure
        MYDUKA/
        ├── server/
        │   ├── routes/
        │   ├── sockets/
        │   ├── tests/
        │   ├── app.py
        │   ├── config.py
        │   ├── extensions.py
        │   ├── models.py
        │   ├── schemas.py
        │   ├── seed.py
        │   ├── .env
        │   └── requirements.txt
        ├── client/
        │   ├── src/
        │   │   ├── components/
        │   │   ├── App.jsx
        │   │   ├── main.jsx
        │   ├── package.json
        │   ├── vite.config.js
        │   └── README.md

#### Setup Instructions
#### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Git

#### Backend Setup

- git clone https://github.com/your-username/myduka.git
- cd myduka/server
- python -m venv venv
- source venv/bin/activate   # Windows: venv\Scripts\activate
- pip install -r requirements.txt

#### Create .env file:

- DATABASE_URL=postgresql://username:password@localhost:5432/myduka
- JWT_SECRET_KEY=your-secret
- MAIL_SERVER=smtp.mailtrap.io
- MAIL_USERNAME=your-username
- MAIL_PASSWORD=your-password

#### Run server:

- python app.py

#### Frontend Setup

- cd ../client
- npm install

#### Create .env file

 - VITE_API_BASE_URL=http://localhost:5000

#### Run app
- npm run dev

#### Database Setup

- psql -U username -c "CREATE DATABASE myduka;"
- cd ../server
- python seed.py
- App will be available at: http://localhost:3000

#### API Endpoints

##### Authentication

- POST /api/auth/login - Login and receive access token.
- POST /api/auth/register - Register via invite token.
- GET /api/auth/google/login - Google OAuth.

##### Users
- GET /api/users?role=ADMIN - List all Admins.
- PUT /api/users/<id>/status - Activate/deactivate user.
- DELETE /api/users/<id> - Delete user.

##### Reports
- GET /api/reports/sales - Sales report.
- GET /api/reports/spoilage - Spoilage report.
- GET /api/inventory/low-stock - Low stock alert.

##### Inventory
- POST /api/inventory/entries - Add stock.
- POST /api/inventory/supply-requests - Request more stock.

##### Future Enhancements

- Implement email notifications for pending requests.
- Add charts comparison across time periods.
- Add audit logs and activity timeline.
- OTP-based password reset.

##### Authors
- Edith Gatwiri - edithgatwiri70@gmail.com
- Elly James - ellykomunga@gmail.com 
- Helen Wairagu - hwangari3@gmail.com
- Ian Gathua - gathuambui@gmail.com
- Edwin Ngigi - edwinngigi313@gmail.com

For any support or issue, feel free to contact us via our emails above.

##### License
This project is licensed under the MIT License.