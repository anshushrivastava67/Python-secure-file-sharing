import streamlit as st
import requests
from datetime import datetime
import os

# Backend API configuration
BACKEND_URL = "http://localhost:8000"  # Update if your backend runs elsewhere

# Initialize session state
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'username' not in st.session_state:
    st.session_state.username = None

def login(username: str, password: str):
    try:
        response = requests.post(
            f"{BACKEND_URL}/token",
            data={"username": username, "password": password, "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            st.session_state.token = response.json()["access_token"]
            st.session_state.user_type = "ops" if username == "opsuser" else "client"
            st.session_state.username = username
            st.success("Logged in successfully!")
            return True
        else:
            st.error("Invalid username or password")
            return False
    except Exception as e:
        st.error(f"Login failed: {str(e)}")
        return False

def logout():
    st.session_state.token = None
    st.session_state.user_type = None
    st.session_state.username = None
    st.success("Logged out successfully!")

def upload_file(file):
    try:
        files = {"file": (file.name, file.getvalue())}
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.post(
            f"{BACKEND_URL}/ops/upload",
            files=files,
            headers=headers
        )
        if response.status_code == 200:
            st.success("File uploaded successfully!")
            return True
        else:
            st.error(f"Upload failed: {response.json().get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        st.error(f"Upload failed: {str(e)}")
        return False

def get_file_list():
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(
            f"{BACKEND_URL}/client/files",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get file list: {response.json().get('detail', 'Unknown error')}")
            return []
    except Exception as e:
        st.error(f"Failed to get file list: {str(e)}")
        return []

def get_download_link(file_id):
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(
            f"{BACKEND_URL}/client/download/{file_id}",
            headers=headers
        )
        if response.status_code == 200:
            return f"{BACKEND_URL}{response.json()['download_link']}"
        else:
            st.error(f"Failed to get download link: {response.json().get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        st.error(f"Failed to get download link: {str(e)}")
        return None

# Streamlit UI
st.title("Secure File Sharing System")

if st.session_state.token is None:
    # Login form
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        login(username, password)
else:
    # Logout button
    st.sidebar.write(f"Logged in as {st.session_state.username} ({st.session_state.user_type})")
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    # Operation User Features
    if st.session_state.user_type == "ops":
        st.header("Upload File")
        uploaded_file = st.file_uploader("Choose a file (PPTX, DOCX, XLSX only)", type=["pptx", "docx", "xlsx"])
        if uploaded_file is not None and st.button("Upload"):
            if upload_file(uploaded_file):
                st.rerun()

    # Client User Features
    elif st.session_state.user_type == "client":
        st.header("Available Files")
        files = get_file_list()
        if files:
            for file in files:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{file['filename']}** (Uploaded by {file['uploaded_by']} on {file['upload_date']})")
                with col2:
                    if st.button("Download", key=f"download_{file['file_id']}"):
                        download_link = get_download_link(file['file_id'])
                        if download_link:
                            st.markdown(f"[Click here to download]({download_link})")
        else:
            st.write("No files available for download")