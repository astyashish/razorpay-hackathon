import requests, time

start = time.time()
with open("examples/teapot.png", "rb") as f:
    r = requests.post(
        "http://localhost:8001/upload",
        files={"file": ("teapot.png", f, "image/png")},
        timeout=300,
    )
elapsed = time.time() - start

print(f"Status: {r.status_code}")
if r.status_code == 200:
    d = r.json()
    print(f"model_url: {d['model_url']}")
    print(f"vertices: {d['vertices']}, faces: {d['faces']}")
    print(f"file_size: {d['file_size']} bytes")
    print(f"Elapsed: {elapsed:.1f}s")
else:
    print(r.text)
