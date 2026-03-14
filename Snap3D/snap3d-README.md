# Snap3D (XeroD Hackathon Edition)

Snap3D is Team XeroD's mobile-first 3D reconstruction app built for the Bangalore c0mpiled Hackathon.

Take one photo, get one interactive 3D model, and download it as GLB/OBJ with real-time status updates.

## Ownership and Usage

- Product integration and hackathon implementation: Team XeroD.
- Core reconstruction model dependency: TripoSR (MIT-licensed upstream).
- Rights for upstream code remain with original copyright holders.
- Rights for XeroD-specific integration changes in this hackathon build belong to Team XeroD.

## Architecture

- Backend: Python FastAPI server on PC/Laptop
- Frontend: React + Vite PWA on mobile browser
- Model: TripoSR + rembg preprocessing
- Transport: REST upload + WebSocket progress
- Viewer: Three.js via React Three Fiber

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt

# Linux/macOS
bash start.sh

# Windows
start.bat

# Manual alternative
cd .. && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host
```

Open frontend URL on mobile using the same Wi-Fi network as backend.

## Pipeline

1. Upload/capture image
2. Background removal and alpha cleanup
3. TripoSR inference
4. Mesh extraction and post-cleaning
5. Optional texture bake
6. Model preview and export

## Feature Highlights

- Live camera capture and preview
- Realtime conversion states over WebSocket
- 3D orbit/zoom/wireframe viewer
- Model history and quick reload
- PWA install support
- Mobile-first responsive UI

## Stack

Backend:
- FastAPI, Uvicorn
- PyTorch, TripoSR, rembg
- trimesh, xatlas, moderngl

Frontend:
- React 18 + TypeScript
- Vite + PWA plugin
- Tailwind CSS
- React Three Fiber + Drei
- Framer Motion + Zustand

## Requirements

- Python 3.10+
- Node.js 18+
- CUDA GPU preferred (CPU fallback works)
- Same local network for phone and backend server

## Hackathon Team

Team Name: XeroD

Maintained for hackathon presentation and judging workflow.
