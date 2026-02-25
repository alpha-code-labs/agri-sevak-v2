import hashlib                                                                                                                                                                                                                                                             
import hmac                                                                                                                                                                                                                                                                
                                                                                                                                                                                                                                                                             
                                                                                                                                                                                                                                                                             
def verify_hmac_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
      """Verify Meta's X-Hub-Signature-256 header against the request body."""                                                                                                                                                                                               
      if not signature_header:                                                     
          return False
      try:
          _, signature_hash = signature_header.split("=", 1)
      except ValueError:
          return False
      expected = hmac.new(app_secret.encode(), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
      return hmac.compare_digest(signature_hash, expected)