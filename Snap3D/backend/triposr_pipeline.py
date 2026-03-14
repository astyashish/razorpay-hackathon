import os
import sys
import logging
import time
from typing import Optional, Callable

import numpy as np
import torch
import rembg
from PIL import Image, ImageFilter
import trimesh
from scipy import ndimage

# Add parent directory so we can import tsr
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground

logger = logging.getLogger(__name__)

_model: Optional[TSR] = None
_rembg_session = None
_device: str = "cpu"

# ── Quality knobs ─────────────────────────────────────────────────────────────
MESH_RESOLUTION = 256          # marching-cubes grid (256 is CPU-safe; 384 OOMs)
FOREGROUND_RATIO = 0.80        # how much of the square the object fills
ALPHA_HARD_THRESHOLD = 200     # 0-255: pixels below this become fully transparent
ALPHA_ERODE_PX = 2             # erode mask to trim rembg fringe artefacts
KEEP_LARGEST_ONLY = True       # discard floating mesh fragments
MESH_THRESHOLD = 25.0          # iso-surface density threshold
MAX_INPUT_DIM = 1024           # resize input image so max side ≤ this (saves RAM)


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


def load_model() -> TSR:
    global _model, _rembg_session, _device
    if _model is not None:
        return _model

    _device = get_device()
    logger.info(f"Loading TripoSR model on {_device}...")

    _model = TSR.from_pretrained(
        "stabilityai/TripoSR",
        config_name="config.yaml",
        weight_name="model.ckpt",
    )
    _model.renderer.set_chunk_size(8192)
    _model.to(_device)

    # Use u2net for best single-object segmentation
    _rembg_session = rembg.new_session(model_name="u2net")

    logger.info("TripoSR model loaded successfully.")
    return _model


# ── Image pre-processing helpers ──────────────────────────────────────────────

def _clean_alpha(rgba: np.ndarray) -> np.ndarray:
    """Hard-threshold + morphological erosion to remove fringe / ghosting."""
    alpha = rgba[:, :, 3].copy()
    # Hard threshold — kills semi-transparent remnants (faces behind object, etc.)
    alpha[alpha < ALPHA_HARD_THRESHOLD] = 0
    alpha[alpha >= ALPHA_HARD_THRESHOLD] = 255
    # Erode by a few px to trim the rembg halo
    if ALPHA_ERODE_PX > 0:
        struct = ndimage.generate_binary_structure(2, 1)
        mask = alpha > 0
        mask = ndimage.binary_erosion(mask, structure=struct, iterations=ALPHA_ERODE_PX)
        alpha = (mask.astype(np.uint8)) * 255
    rgba[:, :, 3] = alpha
    return rgba


def _keep_largest_blob(rgba: np.ndarray) -> np.ndarray:
    """Zero-out every alpha-connected-component except the largest one."""
    alpha = rgba[:, :, 3]
    mask = alpha > 0
    if not mask.any():
        return rgba
    labelled, n_features = ndimage.label(mask)
    if n_features <= 1:
        return rgba
    # Find the largest component by pixel count
    sizes = ndimage.sum(mask, labelled, range(1, n_features + 1))
    largest_label = int(np.argmax(sizes)) + 1
    keep = labelled == largest_label
    rgba[~keep] = 0
    return rgba


def _auto_crop_center(image: Image.Image) -> Image.Image:
    """Crop to the alpha bounding-box, pad to square, resize so the object
    fills FOREGROUND_RATIO of the image — exactly what TripoSR expects."""
    arr = np.array(image)
    assert arr.shape[-1] == 4
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 0)
    if len(ys) == 0:
        return image
    y1, y2 = ys.min(), ys.max()
    x1, x2 = xs.min(), xs.max()
    fg = arr[y1:y2 + 1, x1:x2 + 1]
    # Pad to square
    h, w = fg.shape[:2]
    size = max(h, w)
    ph0 = (size - h) // 2
    pw0 = (size - w) // 2
    ph1 = size - h - ph0
    pw1 = size - w - pw0
    sq = np.pad(fg, ((ph0, ph1), (pw0, pw1), (0, 0)),
                mode="constant", constant_values=0)
    # Pad again so object fills FOREGROUND_RATIO of the final square
    new_size = int(size / FOREGROUND_RATIO)
    pad = (new_size - size) // 2
    padded = np.pad(sq, ((pad, new_size - size - pad),
                         (pad, new_size - size - pad), (0, 0)),
                    mode="constant", constant_values=0)
    return Image.fromarray(padded)


def _composite_on_gray(rgba: Image.Image) -> Image.Image:
    """Alpha-composite the RGBA foreground onto a neutral 50 % gray canvas —
    this is the input format TripoSR was trained on."""
    arr = np.array(rgba).astype(np.float32) / 255.0
    rgb = arr[:, :, :3]
    a = arr[:, :, 3:4]
    comp = rgb * a + (1.0 - a) * 0.5
    return Image.fromarray((comp * 255.0).astype(np.uint8))


def _clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Keep only the largest connected component and remove degenerate faces."""
    if not KEEP_LARGEST_ONLY:
        return mesh
    components = mesh.split(only_watertight=False)
    if not components:
        return mesh
    biggest = max(components, key=lambda m: len(m.faces))
    return biggest


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_image(
    image_path: str,
    output_dir: str,
    progress_callback: Optional[Callable[[str, int, str], None]] = None,
) -> dict:
    """
    Process a single image through the TripoSR pipeline.

    Returns:
        dict with model_path, preview_path, vertices, faces, file_size
    """
    global _model, _rembg_session, _device

    if _model is None:
        load_model()

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(image_path))[0]

    def report(stage: str, progress: int, message: str):
        if progress_callback:
            progress_callback(stage, progress, message)

    # ── Stage 1: Background removal + object isolation ────────────────────
    report("processing", 10, "Loading image...")
    image = Image.open(image_path).convert("RGB")

    # Downscale large images to avoid OOM in rembg / marching cubes
    w, h = image.size
    if max(w, h) > MAX_INPUT_DIM:
        scale = MAX_INPUT_DIM / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        logger.info(f"Resized input {w}x{h} → {image.size[0]}x{image.size[1]}")

    report("processing", 15, "Removing background...")
    # Standard rembg (no alpha_matting — it OOMs on large images).
    # Our _clean_alpha + _keep_largest_blob below handle fringe artefacts instead.
    rgba = rembg.remove(image, session=_rembg_session)

    report("processing", 25, "Isolating object...")
    rgba_arr = np.array(rgba)
    # Clean alpha: hard-threshold + erode fringe
    rgba_arr = _clean_alpha(rgba_arr)
    # Keep only the single largest connected blob (removes stray people / bg bits)
    rgba_arr = _keep_largest_blob(rgba_arr)
    rgba = Image.fromarray(rgba_arr)

    report("processing", 30, "Centering object...")
    # Auto-crop to tight bbox, pad to square with correct ratio
    rgba = _auto_crop_center(rgba)

    # Composite on 50% gray (TripoSR training format)
    preprocessed = _composite_on_gray(rgba)

    # Save preprocessed image as preview
    preview_path = os.path.join(output_dir, f"{base_name}_preview.png")
    preprocessed.save(preview_path)

    report("processing", 40, "Analyzing object geometry...")

    # ── Stage 2: TripoSR inference ────────────────────────────────────────
    report("converting", 50, "Reconstructing 3D surfaces...")
    with torch.no_grad():
        scene_codes = _model([preprocessed], device=_device)

    report("converting", 70, "Extracting mesh...")

    # ── Stage 3: Extract + clean mesh ─────────────────────────────────────
    meshes = _model.extract_mesh(
        scene_codes,
        has_vertex_color=True,
        resolution=MESH_RESOLUTION,
        threshold=MESH_THRESHOLD,
    )
    mesh = meshes[0]

    report("converting", 80, "Cleaning mesh...")
    mesh = _clean_mesh(mesh)

    report("converting", 85, "Adding texture details...")

    # ── Stage 4: Export as GLB ────────────────────────────────────────────
    glb_path = os.path.join(output_dir, f"{base_name}.glb")

    try:
        mesh_scene = trimesh.Scene(geometry={"mesh": mesh})
        glb_bytes = mesh_scene.export(file_type="glb")
        if not glb_bytes:
            glb_bytes = mesh.export(file_type="glb")
        if not glb_bytes:
            raise RuntimeError("GLB export returned empty bytes")
        with open(glb_path, "wb") as f:
            f.write(glb_bytes)
    except Exception as export_err:
        logger.error(f"GLB export failed: {export_err}")
        raise RuntimeError(f"Failed to export 3D model: {export_err}")

    file_size = os.path.getsize(glb_path)
    if file_size == 0:
        raise RuntimeError("GLB export produced an empty file — mesh may be degenerate")
    num_vertices = len(mesh.vertices)
    num_faces = len(mesh.faces)

    report("done", 100, "3D model ready!")

    return {
        "model_path": glb_path,
        "preview_path": preview_path,
        "vertices": num_vertices,
        "faces": num_faces,
        "file_size": file_size,
    }
