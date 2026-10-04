#!/bin/bash

# Run Uvicorn in the background using the '&' operator
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &

# Run Streamlit in the foreground
streamlit run dashboard/app.py
