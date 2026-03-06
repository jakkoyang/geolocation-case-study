import requests
import os
import smtplib
import json
import time
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

ALERT_URL = "coding-challenges+clin-alerts@sprinterhealth.com"
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
    
def parse_status(raw): 
    loc = raw["features"][0]["geometry"]["coordinates"]
    polygons = [] # zone 2 has a hole by nature of polygon
    
    for i in range(1, len(raw["features"])):
        geom = raw["features"][i]["geometry"]
        
        if geom["type"] == "Polygon":
            exterior = geom["coordinates"][0]
            holes = geom["coordinates"][1:]
            polygons.append({"exterior": exterior, "holes": holes})
            
    return loc, polygons

def check_ring(loc, zone): # for a single ring but too lazy to change the name
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

def check(loc, polygons): # uses the old check just in case its a ring (if clinician 2 steps into the ring)
    for poly in polygons: 
        if check_ring(loc, poly["exterior"]):
            in_hole = False 
            
            for hole in poly["holes"]: # if its a ring and its inside
                if check_ring(loc, hole):
                    in_hole = True
                    break
                    
            if not in_hole:
                return True
                
    return False

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

    os.makedirs("unsafe", exist_ok=True) # make the dir if it doesn't exist, ignore if it does
    os.makedirs("safe", exist_ok=True)

    start = time.time()
    run_time = 3600 # 1 hour
    # my laptop shut off halfway because it ran out of battery :(((

    while time.time() - start < run_time:
        for clinician_id in range(1, 8):
            raw = get_status(BASE_URL, clinician_id)

            if raw and "features" in raw: 
                loc, polygons = parse_status(raw)
                is_safe = check(loc, polygons)

                if not is_safe:
                    print(f"Clinician {clinician_id} is out of bounds, sending alert")
                    with open(f"unsafe/raw{clinician_id}.txt", "w") as f: # manual checking for geojson.io
                        json.dump(raw, f, indent=2)
                    send(clinician_id, ALERT_URL)
                else:
                    print(f"Clinician {clinician_id} is safe")
                    with open(f"safe/raw{clinician_id}.txt", "w") as f: # manual checking for geojson.io
                        json.dump(raw, f, indent=2)
            else:
                print(f"Failed to retrieve valid data for clinician {clinician_id}, skip")

        # 40 seconds is too fast! 120 seconds is too slow?
        print("Checked, wait 80 seconds\n")
        time.sleep(80)