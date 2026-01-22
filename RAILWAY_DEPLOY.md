# Railway Deployment Guide

This project is configured for deployment on Railway.

## Quick Deploy

1. **Push to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Configure for Railway deployment"
   git push origin main
   ```

2. **Deploy on Railway**
   - Go to [Railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository: `vipul674/Finlinter`
   - Railway will auto-detect the Python app and deploy

3. **Configuration** (Auto-detected)
   - Railway reads `Procfile` for start command
   - Python version from `requirements.txt`
   - Port automatically assigned via `$PORT` env variable

## Files for Railway

- **`Procfile`** - Tells Railway how to run the app
- **`railway.json`** - Railway-specific configuration
- **`main.py`** - Application entry point
- **`requirements.txt`** - Python dependencies (includes gunicorn)

## Environment Variables

No environment variables required! Everything runs out of the box.

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py
# Or with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "finlinter.web.app:create_app()"
```

## Your App URL

After deployment, Railway will provide a URL like:
`https://your-app.railway.app`

## Advantages over Netlify

- ✅ Native Python/Flask support
- ✅ No serverless function limitations
- ✅ Simpler configuration
- ✅ Better for backend applications
- ✅ Free tier with 500 hours/month

## Troubleshooting

If deployment fails:
1. Check Railway logs in the dashboard
2. Verify all dependencies in requirements.txt
3. Ensure PORT environment variable is used (auto-provided by Railway)
