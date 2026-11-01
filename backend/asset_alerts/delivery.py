"""Real encrypted Web Push. An HTTP acceptance is not proof of OS display."""
import base64,json,re,os
from urllib.parse import urlsplit
from pathlib import Path
import requests
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from pywebpush import webpush,WebPushException
from py_vapid import VapidException

def push_url(value):
    if not isinstance(value,str):raise ValueError('UNTRUSTED_PUSH_ENDPOINT')
    p=urlsplit(value);host=p.hostname or ''
    allowed=host in {'fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com'} or host.endswith('.notify.windows.com') or host.endswith('.push.apple.com')
    if p.scheme!='https' or not allowed or p.username or p.password or p.port not in (None,443) or p.fragment or not p.path or len(value)>3000:raise ValueError('UNTRUSTED_PUSH_ENDPOINT')
    return value

def validate_subscription(value):
    if not isinstance(value,dict) or set(value)-{'endpoint','keys','expirationTime'}:raise ValueError('INVALID_PUSH_SUBSCRIPTION')
    push_url(value.get('endpoint',''))
    if not isinstance(value.get('keys'),dict) or set(value['keys'])!={'p256dh','auth'}:raise ValueError('INVALID_PUSH_KEYS')
    for name,length in [('p256dh',65),('auth',16)]:
        text=value['keys'][name]
        if not isinstance(text,str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,150}={0,2}',text):raise ValueError('INVALID_PUSH_KEYS')
        try:decoded=base64.urlsafe_b64decode(text+'='*((-len(text))%4))
        except Exception:raise ValueError('INVALID_PUSH_KEYS') from None
        if len(decoded)!=length:raise ValueError('INVALID_PUSH_KEYS')
        if name=='p256dh':ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(),decoded)
    return {'endpoint':value['endpoint'],'keys':dict(value['keys'])}

class NoRedirect(requests.Session):
    def request(self,*args,**kwargs):
        kwargs['allow_redirects']=False
        return super().request(*args,**kwargs)

class PushSender:
    def __init__(self,path:Path):
        self.path=path
        path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists():
            key=ec.generate_private_key(ec.SECP256R1())
            try:
                with path.open('xb') as f:f.write(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            except FileExistsError:pass
        self.key=serialization.load_pem_private_key(path.read_bytes(),password=None)
        if not isinstance(self.key,ec.EllipticCurvePrivateKey) or not isinstance(self.key.curve,ec.SECP256R1):raise ValueError('INVALID_VAPID_KEY')
        raw=self.key.public_key().public_bytes(serialization.Encoding.X962,serialization.PublicFormat.UncompressedPoint)
        self.public_key=base64.urlsafe_b64encode(raw).rstrip(b'=').decode()

    def send(self,subscription,payload):
        validate_subscription(subscription)
        encoded=json.dumps(payload,ensure_ascii=False)
        if len(encoded.encode())>3000:raise ValueError('PUSH_PAYLOAD_TOO_LARGE')
        try:
            with NoRedirect() as session:
                session.trust_env=False
                response=webpush(subscription,data=encoded,vapid_private_key=str(self.path),
                    vapid_claims={'sub':os.environ.get('ASSET_ALERTS_VAPID_SUBJECT','https://127.0.0.1')},timeout=5,ttl=86400,requests_session=session)
            status=response.status_code
            return 'PUSH_ACCEPTED' if status in (200,201,202) else 'EXPIRED' if status in (404,410) else 'FAILED'
        except WebPushException as error:
            status=error.response.status_code if error.response is not None else None
            return 'EXPIRED' if status in (404,410) else 'FAILED'
        except (requests.RequestException,OSError,ValueError,VapidException):return 'FAILED'
