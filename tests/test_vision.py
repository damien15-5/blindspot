import numpy as np
import pytest
from PIL import Image

from app.vision import (
    CFG,
    CONDITIONS,
    MANIFEST,
    MODELS,
    decode,
    png,
    predict,
    preprocess,
    sha,
    transform,
)


def test_assets_and_preprocessing():
    for file, digest in MANIFEST["files"].items():
        assert sha((MODELS / file.split("/")[-1]).read_bytes()) == digest
    assert CFG["do_center_crop"] and CFG["do_convert_rgb"] and CFG["do_normalize"]
    assert CFG["do_rescale"] and CFG["do_resize"] and CFG["resample"] == 3
    im = Image.fromarray(
        np.tile(np.arange(400, dtype=np.uint16) % 256, (256, 1)).astype("uint8")
    )
    out = preprocess(im)
    assert out.shape == (1, 3, 224, 224) and out.dtype == np.float32
    np.testing.assert_allclose(
        out[0, :, 0, 0],
        (88 / 255 - np.array(CFG["image_mean"])) / CFG["image_std"],
        atol=1e-6,
    )
    assert preprocess(im.rotate(90, expand=True)).shape == out.shape


def test_repeated_cpu_inference(guitar):
    image = decode(guitar)
    p, a, _ = predict(image)
    q, b, _ = predict(image)
    assert p.shape == (1000,) and abs(p.sum() - 1) < 1e-6 and a == b and len(a) == 5
    np.testing.assert_array_equal(p, q)
    assert a[0]["id"] == 402


@pytest.mark.parametrize("condition", CONDITIONS)
def test_condition_preserves_shape_and_is_deterministic(condition, guitar):
    im = decode(guitar)
    a = transform(im, condition, 1, 42)
    assert a.size == im.size
    assert png(a) == png(transform(im, condition, 1, 42))
    assert png(a) != png(im) and png(a) != png(transform(im, condition, 3, 42))
