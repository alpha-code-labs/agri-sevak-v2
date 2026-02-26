"""Upload 5 evaluation test images to Azure Blob Storage."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.services.blob_storage import BlobStorage


IMAGES = [
    {"local": "/Users/sandeepnair/Desktop/image 1.jpeg", "blob": "eval/wheat_crown_rot.jpeg", "content_type": "image/jpeg"},
    {"local": "/Users/sandeepnair/Desktop/image 2.jpg", "blob": "eval/apple_scab.jpg", "content_type": "image/jpeg"},
    {"local": "/Users/sandeepnair/Desktop/image 3.jpg", "blob": "eval/cotton_boll_rot.jpg", "content_type": "image/jpeg"},
    {"local": "/Users/sandeepnair/Desktop/image 4.jpg", "blob": "eval/maize_southern_rust.jpg", "content_type": "image/jpeg"},
    {"local": "/Users/sandeepnair/Desktop/image 5.png", "blob": "eval/paddy_brown_spot.png", "content_type": "image/png"},
]


async def main():
    blob = BlobStorage()
    for img in IMAGES:
        local_path = Path(img["local"])
        if not local_path.exists():
            print(f"  SKIP: {local_path} not found")
            continue

        data = local_path.read_bytes()
        print(f"  Uploading {local_path.name} ({len(data)//1024}KB) → {img['blob']}...")
        url = await blob.upload(img["blob"], data, content_type=img["content_type"])
        print(f"  OK → {url}")

    print("\nAll uploads complete!")


if __name__ == "__main__":
    asyncio.run(main())
