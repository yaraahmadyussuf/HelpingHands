# Helping Hands 🤝

Helping Hands is a Flask-based web application that connects people who need financial assistance with people who are willing to help.

## 📌 Problem

People who need financial support may have difficulty reaching donors or finding the right people to help them. At the same time, people who want to help may not have an easy way to find genuine help requests.

## 💡 Solution

Helping Hands provides a platform where:

* Requesters can create help requests.
* Donors can browse available help requests.
* Users can search and filter requests by category.
* Donors can offer to help with a request.
* Requesters can see people who offered to help.
* Requesters can edit or delete their own requests.
* Users can manage their requests and support activities.

## 🔄 Main Workflow

```text
User registers / logs in
        ↓
Choose a role
        ↓
┌─────────────────────┐
│                     │
Requester           Donor
│                     │
Create request       Browse requests
│                     │
Request saved        Search / filter
│                     │
Request appears      View details
│                     │
See interested ←──── I Want to Help
helpers
```

## ✨ Main Features

### Authentication

* User registration and login
* Role-based access
* Requester and donor roles
* Password hashing for security
* Login-required routes

### Help Requests

* Create a help request
* Add title and description
* Select a category
* Specify the required amount
* View all approved help requests
* Search requests
* Filter requests by category
* View request details
* Edit your own requests
* Delete your own requests
* View your own requests

### Donor Support

* Donors can offer to help with a request.
* Donors can optionally leave a message.
* Duplicate support for the same request is prevented.
* Requesters can see people who offered to help.
* Donors can view the requests they have offered to help with.

## 🛠️ Technologies Used

* **Python** — main programming language
* **Flask** — web framework and backend
* **SQLite** — database
* **HTML** — webpage structure
* **Jinja2** — dynamic HTML templates
* **CSS** — custom styling
* **Bootstrap** — responsive frontend design
* **Werkzeug** — password hashing and security utilities
* **Git & GitHub** — version control and collaboration

## 📁 Project Structure

```text
Helping-Hands/
│
├── app.py
├── database.py
├── authentication.py
├── seed_data.py
├── requirements.txt
│
├── routes/
│   └── requests.py
│
├── templates/
│   ├── base.html
│   ├── _macros.html
│   └── requests/
│       ├── create.html
│       ├── details.html
│       ├── edit.html
│       ├── list.html
│       ├── my_requests.html
│       └── my_supports.html
│
└── static/
    └── css/
```

## 🚀 How to Run the Project

### 1. Clone the repository

```bash
git clone <repository-url>
```

### 2. Open the project folder

```bash
cd Helping-Hands
```

### 3. Install the required packages

```bash
pip install -r requirements.txt
```

### 4. Add the sample data

```bash
python seed_fake_data.py
```

### 5. Run the Flask application

```bash
python app.py
```

### 6. Open the website

Open the Flask URL shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

## 🔐 Security

The application uses:

* Password hashing with Werkzeug
* Login-required routes
* Role-based access control
* Ownership checks when editing or deleting requests
* Database constraints to help protect stored data

## 🌱 Future Improvements

Possible future features include:

* Online payment/donation system
* Tracking the amount collected from donors
* Notifications
* User profiles
* Request verification
* Admin dashboard
* More advanced donor/requester communication
* Request progress tracking

## 👥 Team Project

Helping Hands was developed as a collaborative project using Git and GitHub, with different team members working on authentication, database functionality, request management, donor support, and frontend design.
Team Members:
Yara Ahmad Yussuf
Gehad Khaled
Sara Khaled
Nour Hisham
Salma Samy
## 📄 License

This project was created for educational purposes and was our NTI graduation project in Python Programming course.
