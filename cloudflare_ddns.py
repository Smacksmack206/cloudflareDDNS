import os
import requests
import sys
import socket

# --- Configuration ---
API_KEY = "dde60f0cac1feaa18f7cd491eb3052a8adb82"
EMAIL = "cvallieu@gmail.com"
ZONE_NAME = "cedricvallieu.qzz.io"
RECORD_NAME = "cedricvallieu.qzz.io"
# --- End Configuration ---

CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4"
HEADERS = {
    "X-Auth-Email": EMAIL,
    "X-Auth-Key": API_KEY,
    "Content-Type": "application/json"
}

def get_external_public_ip():
    """Fetches the current public IP address from an external service."""
    try:
        response = requests.get("https://api.ipify.org?format=json")
        response.raise_for_status()
        ip = response.json()["ip"]
        print(f"Found public IP via external service: {ip}")
        return ip
    except requests.exceptions.RequestException as e:
        print(f"Error fetching public IP from external service: {e}", file=sys.stderr)
        return None

def get_public_ip():
    """Fetches the current public IP address."""
    return get_external_public_ip()

def get_zone_id(zone_name):
    """Fetches the Zone ID for the given zone name."""
    try:
        response = requests.get(f"{CLOUDFLARE_API_URL}/zones", headers=HEADERS, params={"name": zone_name})
        response.raise_for_status()
        zones = response.json()["result"]
        if not zones:
            print(f"Error: Zone '{zone_name}' not found.", file=sys.stderr)
            return None
        return zones[0]["id"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Zone ID: {e}", file=sys.stderr)
        return None

def get_dns_record(zone_id, record_name, record_type):
    """Fetches the DNS record for the given record name and type."""
    try:
        params = {"type": record_type, "name": record_name}
        response = requests.get(f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records", headers=HEADERS, params=params)
        response.raise_for_status()
        records = response.json()["result"]
        if not records:
            return None, None
        return records[0]["id"], records[0]["content"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching DNS record: {e}", file=sys.stderr)
        return None, None

def delete_dns_record(zone_id, record_id):
    """Deletes a DNS record."""
    if not record_id:
        return
    try:
        url = f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records/{record_id}"
        response = requests.delete(url, headers=HEADERS)
        response.raise_for_status()
        print(f"Successfully deleted DNS record {record_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error deleting DNS record: {e}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)

def update_dns_record(zone_id, record_id, new_ip):
    """Updates or creates a DNS record."""
    data = {
        "type": "A",
        "name": RECORD_NAME,
        "content": new_ip,
        "ttl": 1,  # 1 = Automatic
        "proxied": False
    }
    try:
        if record_id:
            # Update existing record
            url = f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records/{record_id}"
            response = requests.put(url, headers=HEADERS, json=data)
        else:
            # Create new record
            url = f"{CLOUDFLARE_API_URL}/zones/{zone_id}/dns_records"
            response = requests.post(url, headers=HEADERS, json=data)
            
        response.raise_for_status()
        print(f"Successfully set DNS record for {RECORD_NAME} to {new_ip}")
    except requests.exceptions.RequestException as e:
        print(f"Error updating DNS record: {e}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)


if __name__ == "__main__":
    print("Starting DDNS update check...")
    public_ip = get_public_ip()
    
    if not public_ip:
        sys.exit(1)

    zone_id = get_zone_id(ZONE_NAME)
    if not zone_id:
        sys.exit(1)

    record_id, current_ip = get_dns_record(zone_id, RECORD_NAME, "A")

    if record_id and public_ip == current_ip:
        print(f"IP address for {RECORD_NAME} is already up to date ({public_ip}). No change needed.")
    else:
        if not record_id:
            print(f"Info: Record '{RECORD_NAME}' of type 'A' not found. Checking for conflicting records.")
            cname_id, _ = get_dns_record(zone_id, RECORD_NAME, "CNAME")
            if cname_id:
                print(f"Found conflicting CNAME record for {RECORD_NAME}. Deleting it...")
                delete_dns_record(zone_id, cname_id)

        print(f"IP address has changed. Current: {current_ip}, New: {public_ip}. Updating...")
        update_dns_record(zone_id, record_id, public_ip)