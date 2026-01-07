#!/usr/bin/env python3
"""Verify local Ollama installation."""

import sys

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: uv add httpx")
    sys.exit(1)


def main():
    host = "http://127.0.0.1:11434"
    
    print(f"Checking Ollama at {host}...")
    
    try:
        resp = httpx.get(f"{host}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        models = data.get("models", [])
        if not models:
            print("No models found. Pull one with: ollama pull llama3.2")
            sys.exit(1)
        
        print(f"Found {len(models)} model(s):")
        for model in models:
            name = model.get("name", "unknown")
            size = model.get("size", 0) / (1024**3)
            print(f"  - {name} ({size:.1f} GB)")
        
        print("\nOllama is ready!")
        
    except httpx.ConnectError:
        print("Cannot connect to Ollama. Is it running?")
        print("Start with: ollama serve")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
