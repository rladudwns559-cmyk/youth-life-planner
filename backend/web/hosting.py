"""Same-origin production hosting. Does not change engine inputs or decisions."""
import os
from pathlib import Path
from urllib.parse import urlsplit
from fastapi.staticfiles import StaticFiles

def production_origin():
    value=(os.environ.get('PUBLIC_BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL') or '').rstrip('/')
    parsed=urlsplit(value)
    if parsed.scheme!='https' or not parsed.hostname or parsed.hostname in ('localhost','127.0.0.1') or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path or parsed.port not in (None,443):
        raise RuntimeError('PRODUCTION_HTTPS_ORIGIN_REQUIRED')
    return value

def configure_production(app):
    if os.environ.get('AIX_ENV')!='production':return
    origin=production_origin()
    directory=Path(os.environ.get('WEB_BUILD_DIR','/app/web')).resolve()
    if not (directory/'index.html').is_file() or not (directory/'assets').is_dir():raise RuntimeError('FRONTEND_BUILD_REQUIRED')
    state=Path(os.environ.get('ASSET_ALERTS_STATE_DIR',''))
    if not state.is_absolute() or str(state) in ('/','/app'):raise RuntimeError('PERSISTENT_ALERT_STATE_REQUIRED')
    if not os.environ.get('ASSET_ALERTS_ORIGINS'):os.environ['ASSET_ALERTS_ORIGINS']=origin
    if not os.environ.get('ASSET_ALERTS_VAPID_SUBJECT'):os.environ['ASSET_ALERTS_VAPID_SUBJECT']=origin
    @app.middleware('http')
    async def production_headers(request,call_next):
        response=await call_next(request)
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        response.headers['Strict-Transport-Security']='max-age=31536000'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
        return response
    # API routes are registered first. StaticFiles serves only the built public
    # directory, never backend source, runtime state, project PDFs or evidence.
    app.mount('/',StaticFiles(directory=directory,html=True),name='public-web')
