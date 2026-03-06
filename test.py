import requests
import os
import smtplib
import json
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

ALERT_URL = "sprinter-eng-test@guerrillamail.info"
BASE_URL = "https://3qbqr98twd.execute-api.us-west-2.amazonaws.com/test"
SENDER_EMAIL = os.getenv("SENDER_EMAIL") # not seeing my real email 
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD") # app password for my real email

def get_status(base_url, clinician_id): # sends requests 
    url = f"{base_url}/clinicianstatus/{clinician_id}"
    
    try: # grabs the response and raises if error
        response = requests.get(url) 
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return None
    
def parse_status(raw): # returns location, and list of zones
    loc = raw["features"][0]["geometry"]["coordinates"]
    zones = [] # now works for multiple polygons, in test 3
    for i in range(1, len(raw["features"])):
        zones.append(raw["features"][i]["geometry"]["coordinates"][0])
    return [loc, zones]

def check(loc, zone): # for a single zone
    crosses = 0
    x, y = loc

    boundaries = []
    points = len(zone)
    for i in range(points - 1): # a type Polygon, points are strictly ordered to trace continuous perimeter
        boundaries.append((zone[i], zone[i+1])) # the last point is the same as the first point, so this is ok

    for p1, p2 in boundaries: # unpack
        x1, y1 = p1
        x2, y2 = p2

        is_horizontal_edge = (y1 == y2 == y) # boundary is horizontal and clinician is on same y
        is_within_x_range = min(x1, x2) <= x <= max(x1, x2)
        
        if is_horizontal_edge and is_within_x_range:
            return False # on the border, so no
            
        if (y1 > y) != (y2 > y): # if between y axis span
            y_distance_to_point = y - y1 # point-slope equation, basic algebra
            y_total_distance = y2 - y1
            y_ratio = y_distance_to_point / y_total_distance
            
            x_total_distance = x2 - x1
            intersect_x = x1 + (x_total_distance * y_ratio)
                
            if x < intersect_x: # to the left of the x intersect (excluding border)
                crosses += 1

            if x == intersect_x: # border check
                return False

    return crosses % 2 != 0 # if only crossed odd times, its inside

def send(c_id, dest_email): # smtplib docs
    msg = EmailMessage()
    msg.set_content(f"Alert, clinician {c_id} is out of their designated safety zone.")
    msg["Subject"] = f"Missing clinician ID: {c_id}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = dest_email

    try: # thanks google
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print(f"Sent email for ID {c_id}")
    except Exception as e:
        print(f"Failed to send email for ID {c_id}: {e}")

if __name__ == "__main__":    

    print("Starting service")

    print("Testing id 3):") # this doesn't work for multiple polygons
    raw = get_status(BASE_URL, 3)
    print(json.dumps(raw, indent=2)) # debugging
    loc, zones = parse_status(raw)
    is_safe = False
    for single_zone in zones:
        if check(loc, single_zone):
            is_safe = True
            break
    print("Safe:", is_safe)

    # print()
    # print("Testing id 7:")
    # raw_7 = get_status(BASE_URL, 7)
    # print(raw_7)
    # print(json.dumps(raw_7, indent=2))
    # loc_7, zone_7 = parse_status(raw_7)
    # safe_7 = check(loc_7, zone_7)