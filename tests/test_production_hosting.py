from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.web.hosting import configure_production,production_origin

@pytest.fixture
def settings(tmp_path,monkeypatch):
    web=tmp_path/'web';(web/'assets').mkdir(parents=True)
    (web/'index.html').write_text('<html><body>public portal</body></html>',encoding='utf-8')
    (web/'assets/app.js').write_text('console.log("portal")',encoding='utf-8')
    (web/'asset-alerts-sw.js').write_text('self.addEventListener("push",()=>{});',encoding='utf-8')
    (tmp_path/'secret.pem').write_text('PRIVATE TEST ONLY',encoding='utf-8')
    monkeypatch.setenv('AIX_ENV','production');monkeypatch.setenv('PUBLIC_BASE_URL','https://portal.example')
    monkeypatch.setenv('WEB_BUILD_DIR',str(web));monkeypatch.setenv('ASSET_ALERTS_STATE_DIR',str(tmp_path/'private-state'))
    monkeypatch.setenv('ASSET_ALERTS_ORIGINS','');monkeypatch.setenv('ASSET_ALERTS_VAPID_SUBJECT','')
    return web
def app():
    a=FastAPI()
    @a.get('/api/health')
    def health():return {'status':'ok'}
    configure_production(a);return a
def test_serves_portal_and_assets_on_same_origin_without_losing_api(settings):
    with TestClient(app()) as c:
        assert c.get('/').status_code==200 and 'public portal' in c.get('/').text
        assert c.get('/assets/app.js').status_code==200
        assert c.get('/asset-alerts-sw.js').status_code==200
        assert c.get('/api/health').json()=={'status':'ok'}
def test_unknown_api_does_not_return_a_fake_html_success(settings):
    with TestClient(app()) as c:assert c.get('/api/not-real').status_code==404
@pytest.mark.parametrize('path',['/secret.pem','/../secret.pem','/%2e%2e/secret.pem','/backend/web/app.py','/tmp/asset-alerts-runtime/vapid-private.pem'])
def test_private_files_are_not_exposed(settings,path):
    with TestClient(app()) as c:
        r=c.get(path);assert r.status_code==404 and 'PRIVATE TEST ONLY' not in r.text
def test_production_security_headers(settings):
    with TestClient(app()) as c:
        for path in ['/','/api/health']:
            h=c.get(path).headers;assert h['x-frame-options']=='DENY' and 'frame-ancestors' in h['content-security-policy'] and 'max-age' in h['strict-transport-security']
def test_correct_public_origin_sets_only_notification_configuration(settings,monkeypatch):
    import os
    before=os.environ.get('EXPLANATION_PROVIDER');app();assert os.environ['ASSET_ALERTS_ORIGINS']=='https://portal.example' and os.environ['ASSET_ALERTS_VAPID_SUBJECT']=='https://portal.example'
    assert os.environ.get('EXPLANATION_PROVIDER')==before
@pytest.mark.parametrize('value',['','http://portal.example','https://localhost','https://127.0.0.1','https://user:pass@portal.example','https://portal.example/path','https://portal.example?token=x','https://portal.example:444'])
def test_invalid_production_origin_is_rejected(settings,monkeypatch,value):
    monkeypatch.setenv('PUBLIC_BASE_URL',value);monkeypatch.delenv('RENDER_EXTERNAL_URL',raising=False)
    with pytest.raises(RuntimeError):production_origin()
def test_render_injected_url_is_supported(settings,monkeypatch):
    monkeypatch.delenv('PUBLIC_BASE_URL');monkeypatch.setenv('RENDER_EXTERNAL_URL','https://site.onrender.com')
    assert production_origin()=='https://site.onrender.com'
def test_missing_build_prevents_false_success(settings,monkeypatch,tmp_path):
    monkeypatch.setenv('WEB_BUILD_DIR',str(tmp_path/'missing'))
    with pytest.raises(RuntimeError,match='FRONTEND_BUILD_REQUIRED'):app()
def test_relative_state_directory_is_rejected(settings,monkeypatch):
    monkeypatch.setenv('ASSET_ALERTS_STATE_DIR','tmp/state')
    with pytest.raises(RuntimeError,match='PERSISTENT_ALERT_STATE_REQUIRED'):app()
def test_local_mode_remains_api_only(monkeypatch):
    monkeypatch.delenv('AIX_ENV',raising=False)
    with TestClient(app()) as c:assert c.get('/').status_code==404 and c.get('/api/health').status_code==200

def entrypoint():
    import importlib.util
    path=Path(__file__).resolve().parents[1]/'deploy/start.py'
    spec=importlib.util.spec_from_file_location('aix_container_entrypoint',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def test_container_uses_one_worker_and_no_access_log(tmp_path,monkeypatch):
    import sys,types
    calls=[];m=entrypoint();monkeypatch.setenv('ASSET_ALERTS_STATE_DIR',str(tmp_path/'state'));monkeypatch.setenv('PORT','12345');monkeypatch.setattr(m.os,'umask',lambda v:None);monkeypatch.setattr(m.os,'getuid',lambda:10001,raising=False)
    monkeypatch.setitem(sys.modules,'uvicorn',types.SimpleNamespace(run=lambda *a,**k:calls.append((a,k))))
    m.main();assert calls[0][1]==dict(host='0.0.0.0',port=12345,workers=1,access_log=False)
def test_container_rejects_relative_private_state(monkeypatch):
    m=entrypoint();monkeypatch.setenv('ASSET_ALERTS_STATE_DIR','relative/state');monkeypatch.setattr(m.os,'umask',lambda v:None);monkeypatch.setattr(m.os,'getuid',lambda:10001,raising=False)
    with pytest.raises(RuntimeError,match='INVALID_STATE_DIRECTORY'):m.main()
def test_container_rejects_invalid_port(tmp_path,monkeypatch):
    m=entrypoint();monkeypatch.setenv('ASSET_ALERTS_STATE_DIR',str(tmp_path/'state'));monkeypatch.setenv('PORT','0');monkeypatch.setattr(m.os,'umask',lambda v:None);monkeypatch.setattr(m.os,'getuid',lambda:10001,raising=False)
    with pytest.raises(RuntimeError,match='INVALID_PORT'):m.main()
