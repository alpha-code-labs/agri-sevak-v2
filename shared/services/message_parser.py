from pydantic import BaseModel, Field                                                                                                                                                                                                                                      
                                                                                                                                                                                                                                                                             
                                                                                                                                                                                                                                                                             
class ParsedMessage(BaseModel):                                                                                                                                                                                                                                            
      id: str
      from_: str = Field(alias="from")                                                                                                                                                                                                                                       
      type: str                                                                    
      phone_number_id: str = ""
      text: str | None = None
      image_id: str | None = None
      audio_id: str | None = None
      location: dict | None = None
      interactive_type: str | None = None
      interactive_id: str | None = None
      interactive_title: str | None = None

      model_config = {"populate_by_name": True}

      @classmethod
      def from_webhook(cls, msg: dict) -> "ParsedMessage":
          """Parse a raw WhatsApp webhook message dict into a ParsedMessage."""
          data = {
              "id": msg.get("id", ""),
              "from": msg.get("from", ""),
              "type": msg.get("type", "text"),
              "phone_number_id": msg.get("phone_number_id", ""),
          }

          msg_type = data["type"]

          if msg_type == "text":
              data["text"] = msg.get("text", {}).get("body")

          elif msg_type == "image":
              data["image_id"] = msg.get("image", {}).get("id")

          elif msg_type == "audio":
              data["audio_id"] = msg.get("audio", {}).get("id")

          elif msg_type == "location":
              data["location"] = msg.get("location", {})

          elif msg_type == "interactive":
              interactive = msg.get("interactive", {})
              data["interactive_type"] = interactive.get("type")
              reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
              data["interactive_id"] = reply.get("id")
              data["interactive_title"] = reply.get("title")

          return cls(**data)
