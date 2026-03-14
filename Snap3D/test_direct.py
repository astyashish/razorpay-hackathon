import sys, traceback
sys.path.insert(0, ".")
from backend.triposr_pipeline import load_model, process_image

def progress(stage, pct, msg):
    print(f"  [{stage}] {pct}% - {msg}")

try:
    load_model()
    result = process_image("examples/teapot.png", "backend/outputs", progress)
    print(f"\nSUCCESS")
    print(f"  vertices: {result['vertices']}")
    print(f"  faces:    {result['faces']}")
    print(f"  size:     {result['file_size']} bytes")
    print(f"  path:     {result['model_path']}")
except Exception as e:
    traceback.print_exc()
