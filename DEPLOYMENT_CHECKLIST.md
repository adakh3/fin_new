# Production Deployment Checklist

## Before Deployment

### 1. Environment Variables
- [ ] Copy `.env.example` to `.env` on your production server
- [ ] Generate a new Django SECRET_KEY for production
- [ ] Set `DJANGO_DEBUG='False'`
- [ ] Update `DJANGO_ALLOWED_HOSTS` with your production domains
- [ ] Add your production API keys (OpenAI, Anthropic, QuickBooks)
- [ ] Update `QB_REDIRECT_URL` to your production URL

### 2. Security Verification
- [ ] Ensure `.env` file is NOT in version control
- [ ] Verify all sensitive data is loaded from environment variables
- [ ] Test that DEBUG is False in production
- [ ] Verify HTTPS is enabled on your server

### 3. Static Files
- [ ] Run `python manage.py collectstatic` to gather static files
- [ ] Configure your web server to serve static files from STATIC_ROOT

### 4. Database
- [ ] Run `python manage.py migrate` on production
- [ ] Consider using PostgreSQL instead of SQLite for production
- [ ] Set up regular database backups

### 5. QuickBooks Integration
- [ ] Verify QuickBooks OAuth redirect URL matches your production domain
- [ ] Test OAuth flow with sandbox credentials first
- [ ] When ready, switch to production QuickBooks app credentials

## Deployment Commands

```bash
# On your production server
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# Restart your application server (gunicorn, etc.)
```

## Post-Deployment

- [ ] Test all OAuth flows
- [ ] Verify SSL certificate is working
- [ ] Check application logs for any errors
- [ ] Test file upload functionality
- [ ] Monitor for any 500 errors

## Security Headers Verification

The following security headers should be active when DEBUG=False:
- Strict-Transport-Security (HSTS)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Secure cookies (HTTPS only)