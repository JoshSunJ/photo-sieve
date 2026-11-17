"""Lazy ML imports: contracts, help, and HTTP tests do not load PyTorch."""

import hashlib
import io
import threading
import warnings
from collections import OrderedDict

from .contracts import ScoreRequest, rank_scores

MODEL_NAME = "ViT-B-32"
PRETRAINED = "laion2b_s34b_b79k"


class ClipScorer:
    def __init__(self, device: str = "auto", cache_size: int = 1024):
        import open_clip
        import torch
        from PIL import Image

        self.torch = torch
        self.Image = Image
        self.Image.MAX_IMAGE_PIXELS = 16_000_000
        if device == "auto":
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.device = device
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=PRETRAINED, device=device
        )
        self.model.eval()
        self.tokenizer = open_clip.get_tokenizer(MODEL_NAME)
        self.cache_size = cache_size
        self.images: OrderedDict = OrderedDict()
        self.texts: OrderedDict = OrderedDict()
        self.lock = threading.Lock()

    def _remember(self, cache: OrderedDict, key, value):
        if self.cache_size > 0:
            cache[key] = value
            cache.move_to_end(key)
            while len(cache) > self.cache_size:
                cache.popitem(last=False)
        return value

    def _image_embedding(self, data: bytes):
        key = hashlib.sha256(data).digest()
        if key in self.images:
            self.images.move_to_end(key)
            return self.images[key]
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", self.Image.DecompressionBombWarning)
                with self.Image.open(io.BytesIO(data)) as image:
                    if image.width > 4096 or image.height > 4096:
                        raise ValueError("Send a thumbnail no larger than 4096 pixels per side")
                    from PIL import ImageOps

                    tensor = self.preprocess(ImageOps.exif_transpose(image).convert("RGB"))
        except (
            OSError,
            self.Image.DecompressionBombError,
            self.Image.DecompressionBombWarning,
        ) as exc:
            raise ValueError("Cannot decode this image safely") from exc
        vector = self.model.encode_image(tensor.unsqueeze(0).to(self.device), normalize=True)
        return self._remember(self.images, key, vector)

    def score(self, request: ScoreRequest) -> dict:
        # One lock protects the model and both caches. The prototype favors predictable
        # memory and correct inference over parallel requests competing for the GPU.
        with self.lock, self.torch.inference_mode():
            image = self._image_embedding(request.image)
            descriptions = request.prompts + request.exclude_prompts
            if descriptions in self.texts:
                self.texts.move_to_end(descriptions)
                text = self.texts[descriptions]
            else:
                tokens = self.tokenizer(list(descriptions)).to(self.device)
                text = self.model.encode_text(tokens, normalize=True)
                self._remember(self.texts, descriptions, text)
            values = (image @ text.T).squeeze(0).float().cpu().tolist()
            count = len(request.prompts)
            result = rank_scores(
                request.prompts,
                values[:count],
                values[count:],
                request.threshold,
                request.margin,
            )
            result["model"] = f"{MODEL_NAME}/{PRETRAINED}"
            return result
