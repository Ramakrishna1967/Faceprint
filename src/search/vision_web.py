from pathlib import Path

from .provider import Candidate


class VisionWebDetection:
    def __init__(self):
        try:
            from google.cloud import vision
        except ImportError as exc:
            raise RuntimeError("Vision fallback requires google-cloud-vision") from exc
        self._vision = vision

    def search(self, image_path: str) -> list[Candidate]:
        client = self._vision.ImageAnnotatorClient()
        image = self._vision.Image(content=Path(image_path).read_bytes())
        result = client.web_detection(image=image)
        if result.error.message:
            raise RuntimeError(result.error.message)
        candidates = []
        for page in result.web_detection.pages_with_matching_images:
            image_url = next(iter(page.full_matching_images or page.partial_matching_images), None)
            if image_url and image_url.url:
                candidates.append(Candidate(page.url, image_url.url, page.page_title, "Google Vision"))
        return candidates
