# PayTrack Backend

A Django REST Framework backend for the PayTrack installment selling application with real-time chat support via WebSockets.

## 🛠 Tech Stack

- **Framework**: Django 4.2 + Django REST Framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **Real-time**: Django Channels (WebSocket)
- **Authentication**: JWT (djangorestframework-simplejwt)
- **Task Scheduling**: APScheduler
- **Storage**: Local / Cloudinary (configurable)

## 📁 Project Structure

```
paytrack-backend/
├── installment_app/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── users/                # User authentication & profiles
│   ├── core/                 # Products, Buyers, Installments
│   │   ├── views/
│   │   │   ├── buyer_views.py
│   │   │   ├── dashboard_views.py
│   │   │   ├── installment_views.py
│   │   │   └── product_views.py
│   │   └── urls/
│   ├── customers/            # Customer management
│   ├── chat/                 # Real-time messaging
│   ├── notifications/        # Push notifications
│   └── media_handler/        # File uploads
├── logs/                     # Application logs
├── manage.py
├── scheduler.py              # Background task scheduler
└── requirements.txt
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- pip
- Virtual environment (recommended)

### Installation

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   Create a `.env` file in the root directory:
   ```env
   DEBUG=True
   SECRET_KEY=your-secret-key
   DATABASE_URL=sqlite:///db.sqlite3
   ALLOWED_HOSTS=localhost,127.0.0.1
   CORS_ALLOWED_ORIGINS=http://localhost:19006,exp://localhost:19000
   ```

4. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run server**
   ```bash
   python manage.py runserver
   ```

## 📝 API Endpoints

### Authentication (`/api/auth/`)
- `POST /register-shopkeeper/` - Register shopkeeper
- `POST /register-buyer/` - Register buyer (shopkeeper only)
- `POST /login/` - User login
- `POST /logout/` - User logout
- `POST /token/refresh/` - Refresh JWT token
- `POST /forgot-password/` - Request password reset OTP
- `POST /verify-otp/` - Verify OTP
- `POST /reset-password/` - Reset password
- `GET /profile/` - Get user profile
- `POST /change-password/` - Change password

### Buyers (`/api/core/buyers/`)
- `GET /` - List buyers
- `POST /` - Create buyer
- `GET /:id/` - Buyer detail
- `PUT /:id/` - Update buyer

### Products (`/api/core/products/`)
- `GET /` - List products
- `POST /` - Create product
- `GET /:id/` - Product detail
- `PUT /:id/` - Update product
- `DELETE /:id/` - Delete product

### Installments (`/api/core/installments/`)
- `GET /` - List installment plans
- `POST /` - Create plan
- `GET /:id/` - Plan detail
- `POST /:id/payments/:paymentId/` - Submit payment

### Customers (`/api/customers/`)
- `GET /` - List customers
- `POST /` - Create customer
- `GET /:id/` - Customer detail

### Chat (`/api/chat/`)
- `GET /conversations/` - List conversations
- `GET /conversations/:id/messages/` - Get messages
- `POST /conversations/:id/messages/` - Send message

### Notifications (`/api/notifications/`)
- `GET /` - List notifications
- `POST /:id/read/` - Mark as read

### Media (`/api/media/`)
- `POST /upload/image/` - Upload image
- `POST /upload/voice/` - Upload voice note

## 🔐 Environment Variables

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:password@localhost:5432/paytrack_db
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:19006,exp://localhost:19000
DEFAULT_FROM_EMAIL=noreply@paytrack.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 🔄 Running Background Tasks

The scheduler handles automated tasks like payment reminders:

```bash
python scheduler.py
```

## 🧪 Running Tests

```bash
python manage.py test
```

## 📦 Deployment

### Using Gunicorn + Nginx

1. **Install Gunicorn**
   ```bash
   pip install gunicorn
   ```

2. **Run with Gunicorn**
   ```bash
   gunicorn installment_app.wsgi:application --bind 0.0.0.0:8000
   ```

### For WebSocket Support (Django Channels)

```bash
daphne -b 0.0.0.0 -p 8000 installment_app.asgi:application
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
