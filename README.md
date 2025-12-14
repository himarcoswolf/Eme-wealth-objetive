# EME Wealth Objetive App

This is a Streamlit application used to calculate and visualize wealth objectives.

## How to Run Locally

1. Ensure you have Python installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Deployment Guide

**IMPORTANT**: This application uses **Python** and **Streamlit**. It CANNOT be deployed directly to Netlify as a static site (like HTML/JS). Netlify is for static content.

### Recommended Deployment: Streamlit Community Cloud (Free)

1. Upload this folder to a GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Connect your GitHub account.
4. Select the repository and the main file `app.py`.
5. Click "Deploy".

If you must use Netlify, you would need to wrap this in a Docker container or use a backend service, which is much more complex. We strongly enable Streamlit Cloud for this type of app.
