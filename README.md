# 🔒 CalVault

CalVault is a Flask-based secure password vault that uses a unique calendar-based authentication system instead of traditional PIN entry.

Users unlock the vault by selecting a predefined sequence of calendar dates followed by a vault password for enhanced security and usability.

---

## 🚀 Features

- 🔐 Calendar-based unlock authentication
- 🗓️ Custom date-sequence security system
- 🔑 Secure password vault management
- ➕ Add, edit, and delete stored passwords
- 📋 Copy credentials instantly
- ⚡ Flask-powered backend
- 🎨 Clean and responsive UI
- 🔒 Password hashing using Werkzeug
- 🧠 Session-based authentication

---

## 🛠️ Tech Stack

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask

### Security
- Werkzeug Password Hashing
- Flask Sessions

### Storage
- JSON-based local storage

---

## 📁 Project Structure

```bash
calvault/
├── app.py               # Flask backend and application logic
├── requirements.txt
├── vault_data.json      # Automatically generated storage file
│
├── templates/
│   ├── base.html
│   ├── setup.html
│   ├── calendar.html
│   ├── unlock.html
│   └── vault.html
│
└── static/
    └── style.css
```

---

## ⚙️ Setup & Run

### 1️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 2️⃣ Run the Application

```bash
python app.py
```

### 3️⃣ Open in Browser

```text
http://127.0.0.1:5000
```

---

## 🔄 Application Flow

### 1️⃣ Setup (`/setup`)
- Create a master PIN using date sequences  
Example:
```text
3-7-14-21
```
- Set a vault password
- Data is securely hashed and stored in `vault_data.json`

### 2️⃣ Calendar Authentication (`/calendar`)
- Select dates in the correct sequence
- Verification happens server-side via `/verify-pin`

### 3️⃣ Unlock Vault (`/unlock`)
- Enter vault password
- Password verified using Werkzeug hashing

### 4️⃣ Vault Dashboard (`/vault`)
- Store and manage passwords
- Add/Edit/Delete credentials
- Copy passwords instantly
- Reset vault and update settings

---

## 🔐 Security Features

- Passwords hashed using Werkzeug (`PBKDF2-SHA256`)
- Calendar sequence validated server-side
- Authentication managed using Flask sessions
- Sensitive data hidden from frontend exposure

### Production Recommendations
- Use a fixed `SECRET_KEY`
- Enable HTTPS
- Store secrets using environment variables


## 🎯 Future Improvements

- Database integration
- User accounts & multi-user support
- Encryption for stored credentials
- Dark mode support
- Cloud backup integration

---

## 👨‍💻 Author

Bhanu Prakash Chintha  
B.Tech CSE (AI & ML)

🔗 GitHub: https://github.com/bhanuprakash2508