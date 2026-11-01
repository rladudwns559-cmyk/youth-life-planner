"""Container entry point: private persistent state, single worker, no access log."""
import os
from pathlib import Path

def main():
    os.umask(0o077)
    state=Path(os.environ.get('ASSET_ALERTS_STATE_DIR','/var/data/asset-alerts'))
    if not state.is_absolute() or str(state) in ('/','/app') or state.is_symlink():raise RuntimeError('INVALID_STATE_DIRECTORY')
    state.mkdir(parents=True,exist_ok=True)
    if os.name=='posix' and os.getuid()==0:
        os.chown(state,10001,10001)
        os.chmod(state,0o700)
        os.setgroups([]);os.setgid(10001);os.setuid(10001)
    port=int(os.environ.get('PORT','10000'))
    if not 1<=port<=65535:raise RuntimeError('INVALID_PORT')
    import uvicorn
    uvicorn.run('backend.web.app:app',host='0.0.0.0',port=port,workers=1,access_log=False)

if __name__=='__main__':main()
