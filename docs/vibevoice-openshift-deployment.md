# VibeVoice vLLM ASR - OpenShift Deployment

OpenShift-kompatibilis Docker image readonly filesystem támogatással.

## Főbb jellemzők

- ✅ **Readonly filesystem**: Minden dependency build-time települ
- ✅ **OpenShift arbitrary UID**: Támogatja az OpenShift által generált random UID-kat (group 0)
- ✅ **PVC támogatás**: Model cache csatolható PVC-ről
- ✅ **FFmpeg pre-installed**: Nincs szükség runtime apt-get-re
- ✅ **Egyszerű permissions**: Csak `chmod -R g=u` és `g+rwX` kell

## Docker Image Build

### Automated Build és Push

```bash
# Windows
build-and-push.bat

# Linux/Mac
chmod +x build-and-push.sh
./build-and-push.sh
```

Ez automatikusan buildi és push-olja az image-t a registry-be: `docker-releases.barre.hu/iqcc/vllm-vibevoice-asr:latest`

### Manuális Build

```bash
# Build az image
docker build -f Dockerfile.openshift -t docker-releases.barre.hu/iqcc/vllm-vibevoice-asr:latest .

# Push registry-be
docker push docker-releases.barre.hu/iqcc/vllm-vibevoice-asr:latest
```

## Használat

### 1. Model auto-download (HuggingFace cache PVC-vel)

```bash
docker run -d --gpus all \
  --name vibevoice-vllm \
  -p 3000:3000 \
  -v /path/to/model-pvc:/mnt/models-data \
  -v /path/to/tmp:/tmp \
  docker-releases.barre.hu/iqcc/vllm-vibevoice-asr:latest
```

### 2. Pre-downloaded model PVC-ről

```bash
docker run -d --gpus all \
  --name vibevoice-vllm \
  -p 3000:3000 \
  -v /path/to/model-pvc:/mnt/models-data \
  -v /path/to/tmp:/tmp \
  docker-releases.barre.hu/iqcc/vllm-vibevoice-asr:latest \
  --model-path /mnt/models-data/VibeVoice-ASR
```

### 3. Custom paraméterek

```bash
docker run -d --gpus all \
  --name vibevoice-vllm \
  -p 8080:8080 \
  -v /path/to/model-pvc:/mnt/models-data \
  -v /path/to/tmp:/tmp \
  docker-releases.barre.hu/iqcc/vllm-vibevoice-asr:latest \
  --model-path /mnt/models-data/VibeVoice-ASR \
  --port 8080 \
  --skip-tokenizer
```

## OpenShift-specifikus beállítások

Az image automatikusan kompatibilis OpenShift-tel:

- **Arbitrary UID**: Nincs explicit USER direktíva, OpenShift random UID-t ad (group 0)
- **Group permissions**: `chmod -R g=u /app` és `chmod -R g+rwX /app /tmp`
- **Readonly filesystem**: Csak a csatolt volume-ok írhatók
- **Home directory**: `HOME=/app` beállítva a writable könyvtárra

### OpenShift Deployment példa

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vibevoice-vllm-asr
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vibevoice-vllm-asr
  template:
    metadata:
      labels:
        app: vibevoice-vllm-asr
    spec:
      containers:
      - name: vibevoice-vllm
        image: docker-releases.barre.hu/iqcc/vllm-vibevoice-asr:latest
        ports:
        - containerPort: 3000
          protocol: TCP
        env:
        - name: HUGGINGFACE_HUB_CACHE
          value: /mnt/models-data
        - name: HF_MODULES_CACHE
          value: /tmp/huggingface/modules
        - name: PYTORCH_ALLOC_CONF
          value: expandable_segments:True
        volumeMounts:
        - name: models-data
          mountPath: /mnt/models-data
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            memory: "8Gi"
            nvidia.com/gpu: "1"
          limits:
            memory: "16Gi"
            nvidia.com/gpu: "1"
      volumes:
      - name: models-data
        persistentVolumeClaim:
          claimName: vibevoice-models-pvc
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: vibevoice-vllm-asr
spec:
  ports:
  - port: 3000
    targetPort: 3000
    protocol: TCP
  selector:
    app: vibevoice-vllm-asr
```

### Writable mount-ok

Az alábbi könyvtárak írhatók (group permissions miatt):

```yaml
# HuggingFace model cache (KÖTELEZŐ - ide letöltődnek a modellek)
mountPath: /mnt/models-data

# HuggingFace modules cache (KÖTELEZŐ - Python modulok cache)
mountPath: /tmp/huggingface/modules
```

Opcionális mount-ok:

```yaml
# Teljes /tmp könyvtár (opcionális, de ajánlott)
mountPath: /tmp

# App cache (opcionális)
mountPath: /app/.cache
```

## Paraméterek

| Paraméter | Leírás | Default |
|-----------|--------|---------|
| `--model` | HuggingFace model ID | `microsoft/VibeVoice-ASR` |
| `--model-path` | Pre-downloaded model path (skip download) | - |
| `--port` | Server port | `3000` |
| `--skip-tokenizer` | Skip tokenizer generation | `false` |
| `--allowed-media-path` | Audio file path | `/app` |

## Environment Variables

| Variable | Leírás | Default |
|----------|--------|---------|
| `HOME` | Home directory | `/app` |
| `HUGGINGFACE_HUB_CACHE` | HuggingFace model cache (PVC mount) | `/mnt/models-data` |
| `HF_MODULES_CACHE` | HuggingFace modules cache | `/tmp/huggingface/modules` |
| `XDG_CACHE_HOME` | XDG cache directory | `/app/.cache` |
| `PYTORCH_ALLOC_CONF` | PyTorch memory config | `expandable_segments:True` |
| `VIBEVOICE_FFMPEG_MAX_CONCURRENCY` | FFmpeg processes | `64` |
| `TMPDIR` | Temp directory | `/tmp` |
| `PYTHONUNBUFFERED` | Python unbuffered output | `1` |
| `PYTHONDONTWRITEBYTECODE` | Skip .pyc files | `1` |

## Tesztelés

```bash
# Check logs
docker logs -f vibevoice-vllm

# Test API
curl -X POST http://localhost:3000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "vibevoice",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "audio_url", "audio_url": {"url": "file:///app/test.wav"}}
        ]
      }
    ]
  }'
```

## Troubleshooting

### Permission denied hibák

Ha permission denied hibát kapsz:

```bash
# Ellenőrizd a PVC ownership-et
ls -la /path/to/pvc

# Ha kell, állítsd be group writable-re
chmod -R g+rwX /path/to/pvc
```

### Model download timeout

Ha a model letöltése timeout-ol:

1. Növeld a container memory limit-et
2. Vagy töltsd le előre a modelt és használd `--model-path`

### FFmpeg hibák

Az FFmpeg már build-time települ, de ha hibaüzenetet kapsz:

```bash
# Ellenőrizd az image-ben
docker exec -it vibevoice-vllm ffmpeg -version
```

## Különbségek az eredeti start_server.py-hoz képest

| Feature | start_server.py | start_server_openshift.py |
|---------|-----------------|---------------------------|
| apt-get install | ✅ Runtime | ❌ Build-time only |
| FFmpeg check | ❌ | ✅ Verify at startup |
| --model-path | ❌ | ✅ Support pre-downloaded |
| --host binding | 127.0.0.1 | 0.0.0.0 (OpenShift) |
| Readonly FS | ❌ | ✅ Compatible |
