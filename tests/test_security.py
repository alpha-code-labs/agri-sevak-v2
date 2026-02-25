import hashlib                                                                                                                                                                                                                                                             
import hmac                                                                                                                                                                                                                                                                
from webhook_receiver.security import verify_hmac_signature                                                                                                                                                                                                                

secret = "test_secret"
body = b"hello world"
sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

assert verify_hmac_signature(body, sig, secret) == True
assert verify_hmac_signature(body, "sha256=wrong", secret) == False
assert verify_hmac_signature(body, None, secret) == False

print("Security OK")