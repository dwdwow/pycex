#!/usr/bin/env python3

try:
    from bnc.spot import ping_spot_endpoint, get_spot_server_time, get_spot_exchange_info
    print("✅ Import successful!")
    print("Functions imported:")
    print("- ping_spot_endpoint")
    print("- get_spot_server_time") 
    print("- get_spot_exchange_info")
except Exception as e:
    print(f"❌ Import failed: {e}")
