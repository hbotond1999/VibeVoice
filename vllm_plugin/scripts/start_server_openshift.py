#!/usr/bin/env python3
"""
VibeVoice vLLM ASR Server Launcher for OpenShift

OpenShift-compatible version that skips system dependency installation
since all dependencies are pre-installed in the Docker image at build time.

This script assumes:
1. System dependencies (FFmpeg, etc.) are already installed
2. VibeVoice package is already installed
3. Filesystem is mostly readonly except mounted volumes
4. Model can be pre-downloaded or mounted from PVC

Usage:
    python3 start_server_openshift.py [--model MODEL_ID] [--port PORT] [--model-path PATH]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str, shell: bool = False) -> None:
    """Run a command with logging."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    if shell:
        subprocess.run(cmd, shell=True, check=True)
    else:
        subprocess.run(cmd, check=True)


def check_system_deps() -> None:
    """Verify system dependencies are installed."""
    print(f"\n{'='*60}")
    print("  Checking system dependencies")
    print(f"{'='*60}\n")
    
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        print("✅ FFmpeg is installed")
        print(f"   Version: {result.stdout.split()[2]}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg not found!")
        sys.exit(1)


def download_model(model_id: str) -> str:
    """Download model from HuggingFace using cache directory."""
    print(f"\n{'='*60}")
    print(f"  Downloading model: {model_id}")
    print(f"  Cache location: {os.environ.get('HUGGINGFACE_HUB_CACHE', os.environ.get('HF_HOME', '~/.cache/huggingface'))}")
    print(f"{'='*60}\n")
    
    import warnings
    from huggingface_hub import snapshot_download
    
    # Suppress deprecation warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model_path = snapshot_download(model_id)
    
    print(f"\n{'='*60}")
    print(f"  ✅ Model downloaded successfully!")
    print(f"  📁 Path: {model_path}")
    print(f"{'='*60}\n")
    return model_path


def generate_tokenizer(model_path: str) -> None:
    """Generate tokenizer files for the model if they don't exist."""
    tokenizer_file = Path(model_path) / "tokenizer.json"
    
    if tokenizer_file.exists():
        print(f"\n{'='*60}")
        print("  ✅ Tokenizer files already exist, skipping generation")
        print(f"{'='*60}\n")
        return
    
    run_command(
        [sys.executable, "-m", "vllm_plugin.tools.generate_tokenizer_files", 
         "--output", model_path],
        "Generating tokenizer files"
    )


def start_vllm_server(model_path: str, port: int, allowed_media_path: str,
                      max_num_seqs: int, max_model_len: int, 
                      max_num_batched_tokens: int, gpu_memory_utilization: float) -> None:
    """Start vLLM server (replaces current process)."""
    print(f"\n{'='*60}")
    print(f"  Starting vLLM server")
    print(f"  Model: {model_path}")
    print(f"  Port: {port}")
    print(f"  Media path: {allowed_media_path}")
    print(f"  Max num seqs: {max_num_seqs}")
    print(f"  Max model len: {max_model_len}")
    print(f"  Max num batched tokens: {max_num_batched_tokens}")
    print(f"  GPU memory utilization: {gpu_memory_utilization}")
    print(f"{'='*60}\n")
    
    vllm_cmd = [
        "vllm", "serve", model_path,
        "--served-model-name", "vibevoice",
        "--trust-remote-code",
        "--dtype", "bfloat16",
        "--max-num-seqs", str(max_num_seqs),
        "--max-model-len", str(max_model_len),
        "--max-num-batched-tokens", str(max_num_batched_tokens),
        "--gpu-memory-utilization", str(gpu_memory_utilization),
        "--enforce-eager",
        "--no-enable-prefix-caching",
        "--enable-chunked-prefill",
        "--chat-template-content-format", "openai",
        "--tensor-parallel-size", "1",
        "--allowed-local-media-path", allowed_media_path,
        "--port", str(port),
        "--host", "0.0.0.0",  # Listen on all interfaces for OpenShift
    ]
    
    # Execute vLLM (replaces current process)
    os.execvp("vllm", vllm_cmd)


def main():
    parser = argparse.ArgumentParser(
        description="VibeVoice vLLM ASR Server - OpenShift Deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Start with auto-download
    python3 start_server_openshift.py

    # Use pre-downloaded model from PVC
    python3 start_server_openshift.py --model-path /models/VibeVoice-ASR

    # Custom port
    python3 start_server_openshift.py --port 8080

    # Skip tokenizer generation (already exists)
    python3 start_server_openshift.py --skip-tokenizer
        """
    )
    parser.add_argument(
        "--model", "-m",
        default="microsoft/VibeVoice-ASR",
        help="HuggingFace model ID (default: microsoft/VibeVoice-ASR)"
    )
    parser.add_argument(
        "--model-path",
        help="Path to pre-downloaded model (skips download if provided)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=3000,
        help="Server port (default: 3000)"
    )
    parser.add_argument(
        "--skip-tokenizer",
        action="store_true",
        help="Skip generating tokenizer files"
    )
    parser.add_argument(
        "--allowed-media-path",
        default="/app",
        help="Allowed local media path for audio files (default: /app)"
    )
    parser.add_argument(
        "--max-num-seqs",
        type=int,
        default=64,
        help="Maximum number of sequences (default: 64)"
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=32768,
        help="Maximum model length (default: 32768)"
    )
    parser.add_argument(
        "--max-num-batched-tokens",
        type=int,
        default=65536,
        help="Maximum number of batched tokens (default: 65536)"
    )
    parser.add_argument(
        "--gpu-memory-utilization",
        type=float,
        default=0.9,
        help="GPU memory utilization (default: 0.9)"
    )
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  VibeVoice vLLM ASR Server - OpenShift Deployment")
    print("="*60)

    # Step 1: Check system dependencies
    check_system_deps()

    # Step 2: Get or download model
    if args.model_path:
        print(f"\n{'='*60}")
        print(f"  Using pre-downloaded model")
        print(f"  📁 Path: {args.model_path}")
        print(f"{'='*60}\n")
        
        if not Path(args.model_path).exists():
            print(f"❌ Model path does not exist: {args.model_path}")
            sys.exit(1)
        
        model_path = args.model_path
    else:
        model_path = download_model(args.model)

    # Step 3: Generate tokenizer files if needed
    if not args.skip_tokenizer:
        generate_tokenizer(model_path)

    # Step 4: Start vLLM server
    start_vllm_server(
        model_path, 
        args.port, 
        args.allowed_media_path,
        args.max_num_seqs,
        args.max_model_len,
        args.max_num_batched_tokens,
        args.gpu_memory_utilization
    )


if __name__ == "__main__":
    main()
