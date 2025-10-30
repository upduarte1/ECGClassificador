# ECG Signal Classifier

A Streamlit application for classifying ECG signals. The system supports user authentication, ECG visualization, and classification logging using Google Sheets.

## Overview

This tool allows users to upload ECG signal data, review each signal, and classify it as *Atrial Fibrillation*, *Sinus Rhythm*, or *Inconclusive*. Each classification is stored for further analysis.

## Features

- User authentication 
- CSV upload of ECG signal data
- ECG signal visualization
- Classification with optional comments
- Automatic synchronization with Google Sheets

## File Structure

```
app.py               # Main Streamlit application
connecting.py        # Google Sheets connection
extracting.py        # ECG signal extraction
plotting.py          # ECG plotting function
requirements.txt     # Python dependencies
```

## Requirements

- Python 3.8 or higher  
- Streamlit  
- gspread  
- oauth2client  
- pandas  
- matplotlib  
- numpy  

Install all dependencies with:

```bash
pip install -r requirements.txt
```

## Usage

1. Clone the repository.  
2. Place your Google API `credentials.json` in the project directory.  
3. Run the application:

   ```bash
   streamlit run main.py
   ```

4. Access the app in your browser.  
5. Log in using authorized credentials.  
6. Upload the ECG CSV file and begin classification.

## Notes

- Usernames, passwords, and roles are defined within the `USERS` and `ROLES` dictionaries in the main script.  
- Classified results are automatically appended to the linked Google Sheet.

## License

This project is intended for academic and research purposes.
