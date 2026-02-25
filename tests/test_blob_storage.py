import asyncio
from shared.services.blob_storage import BlobStorage
from shared.services.config import settings


async def main():
      if not settings.azure_storage_connection_string:
          print("SKIP — no Azure Storage connection string in .env")
          return

      blob = BlobStorage()

      # Upload a test file
      test_data = b"hello from kisaan test"
      url = await blob.upload("test/test_upload.txt", test_data, content_type="text/plain")
      print(f"Upload OK — {url}")

      # Download it back
      downloaded = await blob.download("test/test_upload.txt")
      assert downloaded == test_data
      print("Download OK — content matches")

      print("Blob storage OK")


asyncio.run(main())
