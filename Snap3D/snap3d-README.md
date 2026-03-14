# Snap3D

Turn your photos into 3D models instantly. A full-stack application using TripoSR for single-image 3D reconstruction.

## Architecture

- **Backend**: Python FastAPI server (3D conversion engine, runs on PC)
- **Frontend**: React + Vite PWA (mobile-first, runs on phone browser)
- **3D Engine**: TripoSR (local AI model, runs on PC GPU/CPU)
- **Real-time**: WebSocket for live conversion progress
- **3D Viewer**: Three.js / React Three Fiber

## Quick Start

### PC Setup (Backend Server)

```bash
cd backend
pip install -r requirements.txt

# On Linux/Mac:
bash start.sh

# On Windows:
start.bat

# Or manually:
cd .. && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

A QR code will appear in your terminal — scan it with your phone to get the server URL.

### Mobile Setup (Frontend)

```bash
cd frontend
npm install
npm run dev -- --host
```

Open the displayed URL on your phone browser (both devices must be on the same WiFi).

## How It Works

1. **Start backend** on your PC → get local IP + QR code
2. **Open frontend** on mobile → enter PC IP or scan QR
3. **Take a photo** of any object using your phone camera
4. **Watch real-time** 3D conversion progress via WebSocket
5. **Interact** with your 3D model — rotate, zoom, toggle wireframe
6. **Download** as .GLB or share with others

## Features

- Live camera capture with quality detection
- Real-time conversion progress with 4-stage pipeline
- Interactive 3D model viewer with orbit controls
- Auto-rotate, wireframe toggle
- Model history with search
- PWA installable on home screen
- Premium dark glassmorphism UI
- Responsive mobile-first design

## Tech Stack

### Backend
- FastAPI + Uvicorn
- TripoSR (stabilityai/TripoSR)
- rembg (background removal)
- trimesh (mesh export)
- PyTorch (CUDA/CPU)

### Frontend
- React 18 + TypeScript
- Vite + PWA plugin
- Tailwind CSS v3
- React Three Fiber + Drei
- Framer Motion
- Zustand (state management)
- Lucide React (icons)

## Requirements

- Python 3.10+
- Node.js 18+
- CUDA GPU recommended (CPU fallback available)
- Both devices on the same local network
