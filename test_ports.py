#!/usr/bin/env python3
"""
Test common C-Bus CNI ports to find which one is listening.
"""

import socket
import sys

HOST = "192.168.0.50"

# Common C-Bus CNI ports
COMMON_PORTS = [
    10001,  # Standard CBus TCP port
    20023,  # Clipsal C-Gate port
    502,    # Modbus port (sometimes used)
    1470,   # Another common CBus port
    8080,   # HTTP management
    80,     # HTTP
    23,     # Telnet
    22,     # SSH
]

def test_port(host, port, timeout=3):
    """Test if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def main():
    print(f"🔍 Scanning common C-Bus ports on {HOST}...")
    print("=" * 50)
    
    open_ports = []
    
    for port in COMMON_PORTS:
        print(f"Testing port {port:5d}...", end=" ")
        
        if test_port(HOST, port):
            print("✅ OPEN")
            open_ports.append(port)
        else:
            print("❌ Closed/Filtered")
    
    print("=" * 50)
    
    if open_ports:
        print(f"✅ Found {len(open_ports)} open ports:")
        for port in open_ports:
            print(f"   - {port}")
        print(f"\nTry updating your script to use one of these ports.")
        
        if 20023 in open_ports:
            print(f"\n💡 Port 20023 is open - this is the standard Clipsal C-Gate port!")
        elif 10001 in open_ports:
            print(f"\n💡 Port 10001 is open - this is the standard C-Bus TCP port!")
            
    else:
        print("❌ No common C-Bus ports are open.")
        print("Check your CNI configuration or try a broader port scan.")

if __name__ == "__main__":
    main() 