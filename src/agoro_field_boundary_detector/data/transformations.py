"""Methods for image transformations/augmentations."""
from typing import Callable, Tuple

import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def transform(
    field: np.ndarray,
    mask: np.ndarray,
    translation: Callable[..., Tuple[np.ndarray, np.ndarray]],
    t_idx: int,
    noise: Callable[..., Tuple[np.ndarray, np.ndarray]],
    n_idx: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Transform the field and mask using a translation and noise function."""
    assert translation.__name__ in ("t_linear", "t_quartile", "t_offset")
    assert noise.__name__ in ("t_linear", "t_rotation", "t_flip", "t_blur", "t_gamma")
    field, mask = translation(field, mask, t_idx)
    return noise(field, mask, n_idx)


def t_linear(
    field: np.ndarray,
    mask: np.ndarray,
    _: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Apply a linear (i.e. no) transformation and save."""
    field_t = np.asarray(Image.fromarray(np.uint8(field), "RGB"))
    mask_t = np.asarray(Image.fromarray(np.uint8(mask), "L"))
    return field_t, mask_t


def t_quartile(
    field: np.ndarray,
    mask: np.ndarray,
    idx: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Divide the information into four quarters."""
    assert idx in range(0, 3 + 1)
    x, y = [(0, 0), (0, 1), (1, 0), (1, 1)][idx]
    width, height = mask.shape  # 2d array

    # Slice and recover shape
    field_slice = field[
        (width // 2) * x : (width // 2) * (x + 1), (height // 2) * y : (height // 2) * (y + 1)
    ]
    field_slice = field_slice.repeat(2, axis=0).repeat(2, axis=1)
    mask_slice = mask[
        (width // 2) * x : (width // 2) * (x + 1), (height // 2) * y : (height // 2) * (y + 1)
    ]
    mask_slice = mask_slice.repeat(2, axis=0).repeat(2, axis=1)

    # Normalise masking values
    values = sorted(set(np.unique(mask_slice)) - {0})
    for idx, v in enumerate(values):
        mask_slice[mask_slice == v] = idx + 1
    return field_slice, mask_slice


def t_offset(
    field: np.ndarray,
    mask: np.ndarray,
    offset: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Create a square (half size) under a given offset."""
    width, height = mask.shape  # 2d array

    # Use only half-size as output
    width //= 2
    height //= 2
    assert offset <= min(width, height)

    # Slice and recover shape
    field_slice = field[offset : offset + width, offset : offset + height]
    field_slice = field_slice.repeat(2, axis=0).repeat(2, axis=1)
    mask_slice = mask[offset : offset + width, offset : offset + height]
    mask_slice = mask_slice.repeat(2, axis=0).repeat(2, axis=1)

    # Normalise masking values
    values = sorted(set(np.unique(mask_slice)) - {0})
    for idx, v in enumerate(values):
        mask_slice[mask_slice == v] = idx + 1
    return field_slice, mask_slice


def t_rotation(
    field: np.ndarray,
    mask: np.ndarray,
    rot: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Rotate the data."""
    assert rot in range(0, 3 + 1)
    for _ in range(rot):
        field = np.rot90(field)
        mask = np.rot90(mask)
    return field, mask


def t_flip(
    field: np.ndarray,
    mask: np.ndarray,
    idx: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Flip the data."""
    assert idx in range(0, 2 + 1)
    if idx == 0:  # Diagonal
        field = np.rot90(np.fliplr(field))
        mask = np.rot90(np.fliplr(mask))
    if idx == 1:  # Horizontal
        field = np.flip(field, axis=0)
        mask = np.flip(mask, axis=0)
    if idx == 2:  # Vertical
        field = np.flip(field, axis=1)
        mask = np.flip(mask, axis=1)
    return field, mask


def t_blur(
    field: np.ndarray,
    mask: np.ndarray,
    sigma: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Blur the image by applying a Gaussian filter."""
    field = np.copy(field)
    for i in range(3):
        field[:, :, i] = gaussian_filter(field[:, :, i], sigma=sigma)
    return field, mask


def t_gamma(
    field: np.ndarray,
    mask: np.ndarray,
    gamma: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """Apply gamma correction to the image."""
    assert gamma in range(5, 15 + 1)
    inv_gamma = 1 / (gamma / 10)
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    field = cv2.LUT(field, table)
    return field, mask


# Enlist all augmentation options
TRANSLATION = [
    (t_linear, (0, 0)),
    (t_quartile, (0, 3)),
    (t_offset, (0, 512)),  # Hardcoded 1024//2
]
NOISE = [
    (t_linear, (0, 0)),
    (t_rotation, (0, 3)),
    (t_flip, (0, 2)),
    (t_blur, (1, 3)),
    (t_gamma, (8, 12)),
]
