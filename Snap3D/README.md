# Snap3D by XeroD

Hackathon edition of Snap3D built by Team XeroD for c0mpiled x Magicball x Razorpay Hackathon (Bangalore, 2026).

Snap3D converts a single photo into a usable 3D model with real-time progress updates and mobile-first viewing.

## Project Ownership and Rights

- Hackathon integration, productization, UX, backend orchestration, and deployment workflow: Team XeroD.
- Upstream base 3D reconstruction model: TripoSR by Tripo AI and Stability AI.
- This repository includes upstream MIT-licensed components. See [LICENSE](LICENSE).
- This build is prepared for hackathon demonstration by Team XeroD.

## What Snap3D Does

1. Captures or uploads an image from mobile.
2. Removes background and cleans alpha mask.
3. Runs TripoSR inference locally on GPU/CPU.
4. Extracts mesh and exports GLB/OBJ.
5. Streams progress over WebSocket.
6. Displays model in an interactive 3D viewer.

## System Architecture

- Backend: FastAPI + Uvicorn in [backend/main.py](backend/main.py)
- Pipeline: TripoSR preprocessing/inference in [backend/triposr_pipeline.py](backend/triposr_pipeline.py)
- Frontend: React + Vite PWA in [frontend](frontend)
- 3D Rendering: React Three Fiber + Drei viewer
- Realtime: WebSocket progress channel

## Quick Start

### 1) Backend (PC)

```bash
cd backend
pip install -r requirements.txt

# Linux / macOS
bash start.sh

# Windows
start.bat

# Manual
cd .. && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 2) Frontend (Mobile Web App)

```bash
cd frontend
npm install
npm run dev -- --host
```

Open the shown URL from your phone (same Wi-Fi network as backend machine).

## Manual Inference

```bash
python run.py examples/chair.png --output-dir output/
```

Optional texture bake:

```bash
python run.py examples/chair.png --output-dir output/ --bake-texture --texture-resolution 2048
```

## Troubleshooting

If you see CUDA-related `torchmcubes` errors:

```bash
pip uninstall torchmcubes
pip install git+https://github.com/tatsy/torchmcubes.git
```

Also ensure your local CUDA major version matches the CUDA version used by your PyTorch build.

## Upstream Credits

- TripoSR model card: https://huggingface.co/stabilityai/TripoSR
- TripoSR paper: https://arxiv.org/abs/2403.02151
- TripoSR original authors: Tripo AI and Stability AI

## Team XeroD

Built and demoed by Team XeroD for hackathon judging and live presentation.
