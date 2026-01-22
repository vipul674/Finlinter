# Netlify Deployment Instructions

This project is configured for deployment on Netlify. Follow these steps:

## Deployment Steps

1. **Push to Git Repository**
   ```bash
   git add .
   git commit -m "Configure for Netlify deployment"
   git push
   ```

2. **Connect to Netlify**
   - Go to [Netlify](https://netlify.com)
   - Click "Add new site" → "Import an existing project"
   - Connect your Git repository

3. **Build Settings** (should auto-configure from `netlify.toml`):
   - **Build command**: `pip install -r requirements.txt && mkdir -p netlify/functions`
   - **Publish directory**: `finlinter/web/static`
   - **Functions directory**: `netlify/functions`

4. **Environment Variables** (if needed):
   - `PYTHON_VERSION`: `3.11`

5. **Deploy**
   - Click "Deploy site"
   - Your app will be live at `https://your-site-name.netlify.app`

## Project Structure for Netlify

```
├── netlify.toml              # Netlify configuration
├── runtime.txt               # Python version
├── requirements.txt          # Python dependencies
├── netlify/
│   └── functions/           # Serverless functions
│       ├── scan.py         # Code scanning endpoint
│       └── health.py       # Health check endpoint
└── finlinter/
    └── web/
        └── static/          # Static files (HTML, CSS, JS)
            ├── index.html  # Main page
            ├── style.css   # Styles
            └── app.js      # Frontend logic
```

## API Endpoints

- **Main page**: `https://your-site.netlify.app/`
- **Scan API**: `https://your-site.netlify.app/.netlify/functions/scan`
- **Health check**: `https://your-site.netlify.app/.netlify/functions/health`

## Testing Locally

To test the Netlify functions locally:

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Start local dev server
netlify dev
```

## Troubleshooting

- If build fails, check Python version in runtime.txt matches your requirements
- Ensure all dependencies are listed in requirements.txt
- Check Netlify function logs in the Netlify dashboard
- Static files must be in `finlinter/web/static/` directory
