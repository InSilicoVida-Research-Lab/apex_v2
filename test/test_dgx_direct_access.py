#!/usr/bin/env python3
"""
test/test_dgx_direct_access.py
==============================
Test file for Method 2: Direct Network Access to DGX.

Verifies that the client can connect directly to the DGX server over the local
network or Tailscale/VPN on port 30001 without requiring an SSH tunnel:

    client = OpenAI(
        base_url="http://100.85.128.70:30001/v1",
        api_key="EMPTY"
    )
"""

import sys
import time
import socket

DGX_IP = "100.85.128.70"
DGX_PORT = 30001
BASE_URL = f"http://{DGX_IP}:{DGX_PORT}/v1"
API_KEY = "EMPTY"


def test_socket_connectivity(host: str, port: int, timeout: float = 3.0) -> bool:
    """Fast pre-flight TCP socket check."""
    print(f"[*] Pre-flight check: probing TCP connection to {host}:{port}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        print(f"    [+] Successfully connected to {host}:{port} via TCP.")
        return True
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"    [-] Connection to {host}:{port} failed: {e}")
        print("    [!] Tip: Ensure Tailscale/VPN is active and port 30001 is open on DGX firewall.")
        return False


def test_openai_direct_access():
    """Tests the OpenAI client with direct DGX base_url."""
    try:
        from openai import OpenAI
    except ImportError:
        print("\n[-] The 'openai' package is not installed.")
        print("    Run: pip install openai")
        print("    Attempting raw HTTP fallback test instead...\n")
        return test_http_fallback()

    print("\n" + "=" * 65)
    print(" Testing Method 2: Direct Network Access via OpenAI Client")
    print(f" Base URL: {BASE_URL}")
    print("=" * 65)

    # Initialize client exactly as specified
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )

    # 1. Test listing models
    print("\n[Step 1/2] Fetching available models from DGX...")
    start_t = time.time()
    try:
        models_response = client.models.list()
        elapsed = time.time() - start_t
        model_ids = [m.id for m in models_response.data]
        print(f"    [+] Successfully connected to DGX ({elapsed:.2f}s latency)")
        print(f"    [+] Models found: {model_ids}")
        if not model_ids:
            print("    [-] No models currently loaded in the backend.")
            return False
        active_model = model_ids[0]
    except Exception as e:
        print(f"    [-] Failed to retrieve models: {e}")
        return False

    # 2. Test chat completion
    print(f"\n[Step 2/2] Testing chat completion with model: '{active_model}'...")
    start_t = time.time()
    try:
        response = client.chat.completions.create(
            model=active_model,
            messages=[
                {"role": "user", "content": "Hello! Reply with 'Direct DGX connection confirmed!' in 10 words or less."}
            ],
            max_tokens=50,
            temperature=0.0
        )
        elapsed = time.time() - start_t
        reply_content = response.choices[0].message.content
        print(f"    [+] Response received in {elapsed:.2f}s:")
        print(f"        \"{reply_content.strip()}\"")
        if response.usage:
            print(f"    [+] Tokens: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}, total={response.usage.total_tokens}")
        print("\n" + "=" * 65)
        print(" SUCCESS: Direct DGX Network Access verified!")
        print("=" * 65)
        return True
    except Exception as e:
        print(f"    [-] Chat completion request failed: {e}")
        return False


def test_http_fallback():
    """Raw HTTP test when openai package is not yet installed."""
    import json
    import urllib.request
    import urllib.error

    url = f"{BASE_URL}/models"
    print(f"[*] Querying models via HTTP GET {url}...")
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            print(f"    [+] Direct HTTP connection succeeded! Status: {resp.status}")
            models = [m.get("id") for m in data.get("data", [])]
            print(f"    [+] Available models: {models}")
            return True
    except urllib.error.URLError as e:
        print(f"    [-] HTTP request failed: {e}")
        return False


if __name__ == "__main__":
    tcp_ok = test_socket_connectivity(DGX_IP, DGX_PORT)
    if not tcp_ok:
        sys.exit(1)
    
    success = test_openai_direct_access()
    sys.exit(0 if success else 1)

