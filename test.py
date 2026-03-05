import requests

ALERT_URL = "coding-challenges+clin-alerts@sprinterhealth.com"
BASE_URL = "https://3qbqr98twd.execute-api.us-west-2.amazonaws.com/test"

def get_status(base_url, clinician_id): # sends requests 
    url = f"{base_url}/clinicianstatus/{clinician_id}"
    
    try: # grabs the response and raises if error
        response = requests.get(url) 
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None

if __name__ == "__main__":    
    print("Testing id 1):")
    raw_1 = get_status(BASE_URL, 1)
    print(raw_1)
    
    print()
    print("Testing id 7:")
    raw_7 = get_status(BASE_URL, 7)
    print(raw_7)