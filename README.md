
# **Secure File Sharing System**  
*A FastAPI backend + Streamlit frontend for secure file sharing between Ops and Client users*  

## **Credentials**  
**1. Operation User (Upload Files)**  
- Username: `opsuser`  
- Password: `secret`  

**2. Client User (Download Files)**  
- Username: `clientuser`  
- Password: `secret`  

---

## **⚙️ Setup & Installation**  

### **1. Clone the Repository**  
```bash
git clone https://github.com/your-username/Python-secure-file-sharing.git
cd Python-secure-file-sharing
```

### **2. Install Dependencies**  
```bash
pip install -r requirements.txt
```
*(Ensure Python 3.7+ is installed)*  

### **3. Configure Environment Variables**  
Create a `.env` file in the `backend` folder:  
```env
SECRET_KEY=your-secret-key-here
```

---

## **🚀 Running the System**  

### **Backend (FastAPI)**  
```bash
cd backend
uvicorn main:app --reload
```
- **API Docs**: http://localhost:8000/docs  
- **Default Port**: 8000  

### **Frontend (Streamlit)**  
```bash
cd frontend
streamlit run app.py
```
- **Access UI**: http://localhost:8501  

---

## **📂 File Storage**  
- Uploaded files are saved in: `backend/uploaded_files/`
  
## **🔒 Authentication Flow**  
1. **Login** → Get JWT token  
2. **Ops User** → Upload files (`.pptx`, `.docx`, `.xlsx` only)  
3. **Client User** → List/download files via secure tokens  

### **Deployement**  
1. Push `frontend/app.py` to GitHub.  
2. Deploy via [Streamlit Community Cloud](https://share.streamlit.io).  

### **📬 Contact**  
For issues, email `anshushri0711@gmail.com`.  
