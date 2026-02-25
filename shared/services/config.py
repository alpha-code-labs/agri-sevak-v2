from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
      # WhatsApp
      access_token: str = ""
      app_secret: str = ""
      verify_token: str = "agritech_app"
      graph_api_url: str = "https://graph.facebook.com/v24.0"

      # Kafka
      kafka_bootstrap_servers: str = "localhost:9092"
      kafka_topic_text: str = "farmer-messages-text"
      kafka_topic_image: str = "farmer-messages-image"
      kafka_topic_voice: str = "farmer-messages-voice"

      # Redis
      redis_url: str = "redis://localhost:6379/0"
      redis_cluster_mode: bool = False
      session_ttl_seconds: int = 300
      dedup_ttl_seconds: int = 3600

      # Gemini
      gemini_api_keys: str = ""
      gemini_model_fast: str = "gemini-2.5-flash"
      gemini_model_quality: str = "gemini-3-flash-preview"

      # Pinecone
      pinecone_api_key: str = ""
      pinecone_index_name: str = "kisaan-crops"

      # Azure Blob
      azure_storage_connection_string: str = ""
      azure_storage_container: str = "kcc-agritech-storage"

      # Weather
      weather_api_key: str = ""

      # ML Models
      crop_classifier_model_path: str = "models/crop_classifier"
      sentence_transformer_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

      # Data
      data_dir: str = "shared/data"

      @property
      def gemini_keys_list(self) -> list[str]:
          if not self.gemini_api_keys:
              return []
          return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]
      
      model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()