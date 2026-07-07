# Cartly – Full-Stack E-Commerce Platform

Cartly is a comprehensive, role-based e-commerce web application built with Django. It provides a seamless shopping experience for customers and a robust set of inventory and sales management tools for independent sellers. 

### 🚀 Live Demo
**URL:** [https://shubhammandal.pythonanywhere.com/](https://shubhammandal.pythonanywhere.com/)

To evaluate the platform without registering a new account, please use the following test credentials:

*   **Customer Account** (To test cart, checkout, and order history)
    *   **Username:** `abc`
    *   **Password:** `12345`
*   **Seller Account** (To test product management and sales analytics)
    *   **Username:** `xyz`
    *   **Password:** `54321`

---

## ✨ Key Features

*   **Role-Based Architecture:** Secure, distinct portals and logic for standard consumers (browsing, cart, checkout) and verified sellers (inventory management, analytics).
*   **Bespoke UI/UX Design:** Fully custom frontend architecture using Tailwind CSS and raw HTML forms, explicitly bypassing Django's default template rendering for complete control over styling, animations, and responsiveness.
*   **Secure Payment Integration:** Integrated with the Razorpay API to handle seamless transactions, calculating order totals dynamically and generating strict success/failure statuses.
*   **Seller Analytics Dashboard:** A dedicated portal for vendors to track lifetime revenue, filter sales data by custom date ranges, and update order fulfillment statuses.
*   **Dynamic Cart Management:** Real-time subtotal calculations and stock validation before checkout.
*   **Toast Notification System:** Custom-built, asynchronous slide-in notifications for user feedback (success, errors, warnings) without page disruption.

---

## 🛠️ Technology Stack

*   **Backend:** Python, Django
*   **Frontend:** HTML5, Tailwind CSS, JavaScript (Vanilla)
*   **Database:** SQLite (Development) / configured for deployment
*   **Payment Gateway:** Razorpay API
*   **Hosting:** PythonAnywhere

---

## 💻 Local Installation & Setup

To run this project locally on your machine, follow these steps:

**1. Clone the repository**
```bash
git clone [https://github.com/yourusername/cartly.git](https://github.com/yourusername/cartly.git)
cd cartly

```

**2. Create and activate a virtual environment**

```bash
# Windows
python -m venv env
env\Scripts\activate

# macOS/Linux
python3 -m venv env
source env/bin/activate

```

**3. Install dependencies**

```bash
pip install -r requirements.txt

```

**4. Set up environment variables**
Create a `.env` file in the root directory and add your Razorpay API keys and Django Secret Key:

```env
SECRET_KEY=your_django_secret_key
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret

```

**5. Run database migrations**

```bash
python manage.py makemigrations
python manage.py migrate

```

**6. Create a superuser (optional, for admin access)**

```bash
python manage.py createsuperuser

```

**7. Start the development server**

```bash
python manage.py runserver

```

Navigate to `http://127.0.0.1:8000` in your browser to view the application.

---

