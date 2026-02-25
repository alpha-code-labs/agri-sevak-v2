import asyncio                                                                                                                                                                                                                                                             
from azure.storage.blob import BlobServiceClient, ContentSettings                                 
from shared.services.config import settings                                                                                                                                                                                                                                
                                                                                   

class BlobStorage:
      def __init__(self, connection_string: str = "", container_name: str = ""):
          self.connection_string = connection_string or settings.azure_storage_connection_string
          self.container_name = container_name or settings.azure_storage_container

      async def upload(self, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
          """Upload bytes to Azure Blob Storage. Returns the blob URL."""
          def _upload():
              client = BlobServiceClient.from_connection_string(self.connection_string)
              blob_client = client.get_blob_client(container=self.container_name, blob=blob_name)
              blob_client.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))
              return blob_client.url

          return await asyncio.to_thread(_upload)

      async def download(self, blob_name: str) -> bytes:
          """Download bytes from Azure Blob Storage."""
          def _download():
              client = BlobServiceClient.from_connection_string(self.connection_string)
              blob_client = client.get_blob_client(container=self.container_name, blob=blob_name)
              return blob_client.download_blob().readall()

          return await asyncio.to_thread(_download)