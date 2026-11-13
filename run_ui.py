#!/usr/bin/env python3
"""APEX PBPK UI Server Entrypoint.

Usage:
    python run_ui.py [--port 8050] [--host 0.0.0.0]
"""

import argparse
import socket
import sys
import uvicorn

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def find_available_port(preferred_port: int, host: str = "127.0.0.1") -> int:
    port = preferred_port
    while is_port_in_use(port, host):
        port += 1
    return port

def main():
    parser = argparse.ArgumentParser(description="Start APEX PBPK Extraction & Audit Dashboard")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8050, help="Port to listen on (default: 8050)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")
    args = parser.parse_args()

    port = args.port
    if is_port_in_use(port, "127.0.0.1"):
        new_port = find_available_port(port + 1, "127.0.0.1")
        print(f"\n[NOTICE] Port {port} is already in use by another service on this machine.")
        print(f"[NOTICE] Automatically redirected to available port {new_port}.\n")
        port = new_port

    print(f"\n{'='*65}")
    print(f"  APEX PBPK EXTRACTION & QUALITY AUDIT DASHBOARD")
    print(f"{'='*65}")
    print(f"  • Web Dashboard:  http://localhost:{port}")
    print(f"  • REST API Docs:  http://localhost:{port}/docs")
    print(f"  • Bind Host:      {args.host}")
    print(f"{'='*65}\n")

    uvicorn.run("pk_pipeline.api_server:app", host=args.host, port=port, reload=args.reload)

if __name__ == "__main__":
    main()
