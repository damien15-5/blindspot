import hashlib
import io
import json
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
MANIFEST = json.loads((MODELS / "manifest.json").read_text())
MODEL = MANIFEST["files"]["onnx/model_quantized.onnx"]
PRE = MANIFEST["files"]["preprocessor_config.json"]
CFG = json.loads((MODELS / "preprocessor_config.json").read_text())
LABELS = json.loads((MODELS / "config.json").read_text())["id2label"]
CONDITIONS = ("low light", "blur", "JPEG", "rotation", "occlusion", "colour cast", "glare")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def preprocess(image):
    image = image.convert("RGB")
    w, h = image.size
    edge = CFG["size"]["shortest_edge"]
    w, h = (edge, edge*h//w) if w <= h else (edge*w//h, edge)
    image = image.resize((w, h), Image.Resampling(CFG["resample"]))
    cw, ch = CFG["crop_size"]["width"], CFG["crop_size"]["height"]
    x, y = (w-cw)//2, (h-ch)//2
    pixels = np.asarray(image.crop((x, y, x+cw, y+ch)), dtype=np.float32)
    pixels *= CFG["rescale_factor"]
    pixels -= np.asarray(CFG["image_mean"], dtype=np.float32)
    pixels /= np.asarray(CFG["image_std"], dtype=np.float32)
    return np.ascontiguousarray(pixels.transpose(2, 0, 1)[None])


@lru_cache(maxsize=1)
def session():
    for name, digest in MANIFEST["files"].items():
        if sha((MODELS / Path(name).name).read_bytes()) != digest:
            raise ValueError(f"Invalid pinned asset {name}")
    options = ort.SessionOptions()
    options.intra_op_num_threads = options.inter_op_num_threads = 1
    return ort.InferenceSession(str(MODELS / "model_quantized.onnx"), options,
                                providers=["CPUExecutionProvider"])


def predict(image):
    start = time.process_time_ns()
    model = session()
    raw = model.run(["logits"], {"pixel_values": preprocess(image)})[0][0]
    probs = np.exp(raw - raw.max())
    probs /= probs.sum()
    top = [dict(id=int(i), label=LABELS[str(i)], score=float(probs[i]))
           for i in np.argsort(-probs, kind="stable")[:5]]
    return probs, top, (time.process_time_ns()-start)/1e6


def transform(image, condition, level, seed):
    # Severity levels preserve the full canvas and use a deterministic occluder side.
    i = level - 1
    if condition == "low light":
        return ImageEnhance.Brightness(image).enhance([.65,.35,.16][i])
    if condition == "blur":
        return image.filter(ImageFilter.GaussianBlur([1.2,3,6][i]))
    if condition == "JPEG":
        buf = io.BytesIO()
        image.save(buf, "JPEG", quality=[30,12,4][i])
        return Image.open(buf).convert("RGB")
    if condition == "rotation":
        return image.rotate([8,16,25][i], Image.Resampling.BICUBIC)
    if condition == "colour cast":
        r,g,b = image.split()
        return Image.merge("RGB",(r,g.point(lambda x:x*(1-.12*level)),b.point(lambda x:x*(1-.23*level))))
    result = image.copy()
    w,h = image.size
    if condition == "occlusion":
        width = w*(.1+.06*level)
        x = 0 if seed % 2 else w-width
        ImageDraw.Draw(result).rectangle((x,0,x+width,h),fill=(84,82,80))
    elif condition == "glare":
        overlay = Image.new("RGB", image.size, "white")
        mask = Image.new("L", image.size)
        ImageDraw.Draw(mask).ellipse((w*.25,0,w*.75,h*.65),fill=50+50*level)
        result = Image.composite(overlay,image,mask.filter(ImageFilter.GaussianBlur(w*.08)))
    else:
        raise ValueError("Unknown camera condition")
    return result


def png(image):
    buf = io.BytesIO()
    image.save(buf, "PNG")
    return buf.getvalue()


def decode(data):
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in ("JPEG", "PNG", "WEBP") or max(image.size)>4096 or image.width*image.height>8000000:
            raise ValueError("Use JPEG, PNG or WebP up to 4096 px and 8 megapixels")
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((768,768), Image.Resampling.LANCZOS)
        return image
