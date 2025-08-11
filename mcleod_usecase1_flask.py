import logging
from flask import Flask
from flask import jsonify, request
from pymongo import MongoClient
from datetime import datetime
import requests
import json
import configparser
from flask_cors import CORS
from jsonschema import validate, ValidationError
from functools import wraps

config = configparser.ConfigParser()
config.read('config.ini')

app = Flask(__name__)
CORS(app)

with open('schema.json') as f:
    schema = json.load(f)

def validate_json(schema):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = request.get_json(force=True)
                validate(instance=data, schema=schema)
            except ValidationError as e:
                return jsonify({"error": "Invalid request data", "details": e.message}), 400
            except Exception as e:
                return jsonify({"error": "Malformed or missing JSON data", "details": str(e)}), 400
            return func(*args, **kwargs)
        return wrapper
    return decorator

# ========== MONGO SETUP ==========
MONGO_URI = config.get('mongodb', 'uri')
DB_NAME = config.get('mongodb', 'db')
MAPBOX_ACCESS_TOKEN = config.get('mapbox', 'access_token')

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# ========== DATA ==========
cities = [
    {"city": "New York", "state": "NY", "latitude": 40.7128, "longitude": -74.0060},
    {"city": "Los Angeles", "state": "CA", "latitude": 34.0522, "longitude": -118.2437},
    {"city": "Chicago", "state": "IL", "latitude": 41.8781, "longitude": -87.6298},
    {"city": "Houston", "state": "TX", "latitude": 29.7604, "longitude": -95.3698},
    {"city": "Phoenix", "state": "AZ", "latitude": 33.4484, "longitude": -112.0740},
    {"city": "Philadelphia", "state": "PA", "latitude": 39.9526, "longitude": -75.1652},
    {"city": "San Antonio", "state": "TX", "latitude": 29.4241, "longitude": -98.4936},
    {"city": "San Diego", "state": "CA", "latitude": 32.7157, "longitude": -117.1611},
    {"city": "Dallas", "state": "TX", "latitude": 32.7767, "longitude": -96.7970},
    {"city": "San Jose", "state": "CA", "latitude": 37.3382, "longitude": -121.8863},
    {"city": "Austin", "state": "TX", "latitude": 30.2672, "longitude": -97.7431},
    {"city": "Jacksonville", "state": "FL", "latitude": 30.3322, "longitude": -81.6557},
    {"city": "Fort Worth", "state": "TX", "latitude": 32.7555, "longitude": -97.3307},
    {"city": "Columbus", "state": "OH", "latitude": 39.9612, "longitude": -82.9988},
    {"city": "Charlotte", "state": "NC", "latitude": 35.2271, "longitude": -80.8431},
    {"city": "Indianapolis", "state": "IN", "latitude": 39.7684, "longitude": -86.1581},
    {"city": "San Francisco", "state": "CA", "latitude": 37.7749, "longitude": -122.4194},
    {"city": "Seattle", "state": "WA", "latitude": 47.6062, "longitude": -122.3321},
    {"city": "Denver", "state": "CO", "latitude": 39.7392, "longitude": -104.9903},
    {"city": "Washington", "state": "DC", "latitude": 38.9072, "longitude": -77.0369},
    {"city": "Birmingham", "state": "AL", "latitude": 33.5207, "longitude": -86.8025},
    {"city": "Montgomery", "state": "AL", "latitude": 32.3792, "longitude": -86.3077},
    {"city": "Huntsville", "state": "AL", "latitude": 34.7304, "longitude": -86.5861},
    {"city": "Mobile", "state": "AL", "latitude": 30.6954, "longitude": -88.0399},
    {"city": "Tuscaloosa", "state": "AL", "latitude": 33.2096, "longitude": -87.5692},
    {"city": "Dothan", "state": "AL", "latitude": 31.2238, "longitude": -85.3905},
    {"city": "Hoover", "state": "AL", "latitude": 33.3857, "longitude": -86.8092},
    {"city": "Auburn", "state": "AL", "latitude": 32.6099, "longitude": -85.4808},
    {"city": "Decatur", "state": "AL", "latitude": 34.6067, "longitude": -86.9833},
    {"city": "Florence", "state": "AL", "latitude": 34.7998, "longitude": -87.6775},
    {"city": "Nashville", "state": "TN", "latitude": 36.1627, "longitude": -86.7816},
    {"city": "Memphis", "state": "TN", "latitude": 35.1495, "longitude": -90.0490},
    {"city": "Knoxville", "state": "TN", "latitude": 35.9606, "longitude": -83.9207},
    {"city": "Chattanooga", "state": "TN", "latitude": 35.0457, "longitude": -85.3097},
    {"city": "Clarksville", "state": "TN", "latitude": 36.5298, "longitude": -87.3595},
    {"city": "Murfreesboro", "state": "TN", "latitude": 35.8450, "longitude": -86.3904},
    {"city": "Franklin", "state": "TN", "latitude": 35.9259, "longitude": -86.8681},
    {"city": "Jackson", "state": "TN", "latitude": 35.6145, "longitude": -88.8136},
    {"city": "Johnson City", "state": "TN", "latitude": 36.3134, "longitude": -82.3530},
    {"city": "Kingsport", "state": "TN", "latitude": 36.5498, "longitude": -82.5613},
]
carrier_scac_dict = {
    "Carrier A" : "LGCA", "Carrier B" : "LGCB", "Carrier C" : "LGCC", "Carrier D" : "LGCD",
    "Carrier E" : "LGCE", "Carrier F" : "LGCF", "Carrier G" : "LGCG", "Carrier H" : "LGCH",
    "Carrier I" : "LGCI", "Carrier J" : "LGCJ", "Carrier K" : "LGCK", "Carrier L" : "LGCL",
    "Carrier M" : "LGCM", "Carrier N" : "LGCN", "Carrier O" : "LGCO"
}

MAPBOX_ACCESS_TOKEN = config.get('mapbox', 'access_token')

# ========== HELPERS ==========
def get_city_coords(city_name):
    city = next((c for c in cities if c["city"].strip().lower() == city_name.strip().lower()), None)
    if city:
        return city["latitude"], city["longitude"]
    return None, None

def get_mapbox_route(origin, destination, token):
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/" \
          f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}" \
          f"?geometries=geojson&access_token={token}"
    resp = requests.get(url)
    if resp.status_code == 200:
        data = resp.json()
        coords = data["routes"][0]["geometry"]["coordinates"]
        route = [{"lat": lat, "lon": lon} for lon, lat in coords]
        return route
    else:
        logging.error(f"Mapbox error: {resp.text}")
        return None

def km_to_miles(km):
    try: return round(float(km) * 0.621371, 2)
    except: return km

def tons_to_kg(tons):
    return tons * 1000

# ========== LOG REQUESTS ==========
def log_request():
    logging.info(f"{request.remote_addr} - {request.method} {request.url} - {request.get_json(silent=True)}")

@app.before_request
def before():
    log_request()

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Exception: {str(e)}", exc_info=True)
    return jsonify({"error": "Internal server error", "details": str(e)}), 500

# ========== BOOKING SECTION APIS ==========

@app.route('/dropdown-data', methods=['GET'])
def dropdown_data():
    try:
        carrier_names = [c["name"] for c in db.carrier_partners.find({}, {"name":1})]
        truck_types = list(db.trucks.distinct("truck_type"))
        all_origins = sorted(set([o.strip().title() for o in db.lanes.distinct("origin")]))
        all_destinations = sorted(set([d.strip().title() for d in db.lanes.distinct("destination")]))
        lane_ids = [l["lane_id"] for l in db.lanes.find({}, {"lane_id":1})]
        return jsonify({
            "carrier_names": carrier_names,
            "truck_types": truck_types,
            "all_origins": all_origins,
            "all_destinations": all_destinations,
            "lane_ids": lane_ids,
        })
    except Exception as e:
        logging.error(f"/dropdown-data error: {str(e)}", exc_info=True)
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/carriers", methods=["GET"])
def get_carriers():
    try:
        carrier_names = [c["name"] for c in db.carrier_partners.find({}, {"name":1})]
        return jsonify(carrier_names)
    except Exception as e:
        logging.error(f"/carriers error: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/truck-types", methods=["GET"])
def get_truck_types():
    try:
        truck_types = list(db.trucks.distinct("truck_type"))
        
        formatted_truck_types = [
            t.replace("_", " ").title() for t in truck_types if isinstance(t, str)
        ]
        
        return jsonify(formatted_truck_types)
    except Exception as e:
        logging.error(f"/truck-types error: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/origins", methods=["GET"])
def get_origins():
    try:
        origins = sorted(set([o.strip().title() for o in db.lanes.distinct("origin")]))
        return jsonify(origins)
    except Exception as e:
        logging.error(f"/origins error: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/destinations", methods=["GET"])
def get_destinations():
    try:
        destinations = sorted(set([d.strip().title() for d in db.lanes.distinct("destination")]))
        return jsonify(destinations)
    except Exception as e:
        logging.error(f"/destinations error: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route("/lane-ids", methods=["GET"])
def get_lane_ids():
    try:
        lane_ids = [l["lane_id"] for l in db.lanes.find({}, {"lane_id":1})]
        return jsonify(lane_ids)
    except Exception as e:
        logging.error(f"/lane-ids error: {str(e)}")
        return jsonify({"error": "Server error"}), 500

@app.route('/lane-details', methods=['POST'])
@validate_json(schema)
def lane_details():
    try:
        data = request.json
        origin = data.get("origin")
        destination = data.get("destination")
        if not origin or not destination:
            return jsonify({"error": "Missing origin or destination"}), 400
        lane = db.lanes.find_one(
            {"origin": origin.strip().title(), "destination": destination.strip().title()},
            {"_id": 0, "distance": 0}
        )
        # Fetch distance in a separate query for calculation
        distance_doc = db.lanes.find_one(
            {"origin": origin.strip().title(), "destination": destination.strip().title()},
            {"distance": 1}
        )
        distance_km = distance_doc.get("distance", 0) if distance_doc else 0

        if lane:
            lane["distance_miles"] = km_to_miles(distance_km)
            return json.dumps(lane)
        else:
            return jsonify({"error": "Not found"}), 404
    except Exception as e:
        logging.error(f"/lane-details error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/carrier-id', methods=['POST'])
@validate_json(schema)
def carrier_id():
    try:
        carrier_name = request.json.get("carrier_name")
        carrier = db.carrier_partners.find_one({"name": carrier_name})
        print(carrier)
        if carrier:
            return jsonify({"carrier_id": carrier["carrier_id"], "scac_code": carrier['scac_code']}) 
        else:
            jsonify({"error": "Not found"}), 404
    except Exception as e:
        logging.error(f"/carrier-id error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/available-trucks', methods=['POST'])
@validate_json(schema)
def available_trucks():
    try:
        d = request.json
        carrier_id, truck_type, schedule_date = d.get("carrier_id"), d.get("truck_type"), d.get("schedule_date")
        trucks = list(db.trucks.find({
            "carrier_id": carrier_id, "truck_type": truck_type, "status": "unbooked"
        }))
        booked_truck_ids = [b["truck_id"] for b in db.booking.find({
            "carrier_id": carrier_id,
            "schedule_date": schedule_date,
            "booking_status": {"$in": ["Confirmed", "Pending"]}
        },{"truck_id":1})]
        available = [t["truck_id"] for t in trucks if t["truck_id"] not in booked_truck_ids]
        return jsonify({"available_trucks": available})
    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/book-shipment", methods=["POST"])
@validate_json(schema)
def api_book_shipment():
    try:
        data = request.json
        user_id = data.get("user_id")
        carrier_name = data.get("carrier_name")
        lane_id = data.get("lane_id")
        origin = data.get("origin")
        destination = data.get("destination")
        schedule_date = data.get("schedule_date")
        weight = data.get("weight")
        volume = data.get("volume")
        truck_type = data.get("truck_type")

        # Validate required inputs
        if not all([user_id, carrier_name, lane_id, origin, destination, schedule_date, weight, volume, truck_type]):
            return jsonify({"success": False, "msg": "Missing required fields"}), 400

        # Find carrier_id from carrier_name
        carrier = db.carrier_partners.find_one({"name": carrier_name})
        if not carrier:
            return jsonify({"success": False, "msg": "Carrier not found"}), 404
        carrier_id = carrier["carrier_id"]

        # Check availability for the requested carrier and truck_type
        trucks = list(db.trucks.find({
            "carrier_id": carrier_id,
            "truck_type": truck_type,
            "status": "unbooked"
        }))
        booked_truck_ids = [b["truck_id"] for b in db.booking.find({
            "carrier_id": carrier_id,
            "schedule_date": schedule_date,
            "booking_status": {"$in": ["Confirmed", "Pending"]}
        }, {"truck_id": 1})]
        available_trucks = [t for t in trucks if t["truck_id"] not in booked_truck_ids]

        if available_trucks:
            # Allocate first available truck and book
            truck_id = available_trucks[0]["truck_id"]
            booking_data = {
                "shipment_id": f"SHP_{datetime.now().timestamp()}",
                "user_id": user_id,
                "carrier_id": carrier_id,
                "truck_id": truck_id,
                "lane_id": lane_id,
                "origin": origin,
                "destination": destination,
                "booking_date": datetime.now().strftime("%Y-%m-%d"),
                "booking_time": datetime.now().strftime("%H:%M:%S"),
                "schedule_date": schedule_date,
                "weight": weight,
                "volume": volume,
                "truck_type": truck_type,
                "booking_status": "Confirmed",
                "suggested_date": None,
                "created_at": datetime.now()
            }
            db.booking.insert_one(booking_data)
            return jsonify({
                "success": True,
                "msg": "Shipment booked successfully!",
                "allocated_truck_id": truck_id
            })

        # If no trucks available for requested carrier/truck_type
        # Check other carriers (excluding requested) for availability of same truck_type
        alternative_carriers = []
        other_carriers = list(db.carrier_partners.find({"carrier_id": {"$ne": carrier_id}}, {"carrier_id":1, "name":1}))
        for c in other_carriers:
            c_id = c["carrier_id"]
            trucks = list(db.trucks.find({
                "carrier_id": c_id,
                "truck_type": truck_type,
                "status": "unbooked"
            }))
            booked_ids = [b["truck_id"] for b in db.booking.find({
                "carrier_id": c_id,
                "schedule_date": schedule_date,
                "booking_status": {"$in": ["Confirmed", "Pending"]}
            }, {"truck_id":1})]
            available = [t for t in trucks if t["truck_id"] not in booked_ids]
            if available:
                alternative_carriers.append({
                    "carrier_name": c["name"],
                    "available_trucks_count": len(available)
                })

        if alternative_carriers:
            return jsonify({
                "success": False,
                "msg": ("The requested carrier does not have available trucks of the requested type for the chosen date. "
                        "However, the following carriers have availability for the same truck type:"),
                "alternative_carriers": alternative_carriers
            }), 400

        # No trucks of requested truck_type available with any carrier on that date
        return jsonify({
            "success": False,
            "msg": f"No trucks of type '{truck_type}' are available with any carrier for the chosen date."
        }), 400

    except Exception as e:
        logging.error(f"/book-shipment error: {str(e)}")
        return jsonify({"success": False, "msg": f"Error booking shipment: {e}"}), 500


# @app.route('/suggest-alternatives', methods=['POST'])
# def suggest_alternative_carriers():
#     try:
#         d = request.json
#         excluded_carrier_id = d.get("excluded_carrier_id")
#         truck_type = d.get("truck_type")
#         schedule_date = d.get("schedule_date")
#         suggestions = []
#         all_carriers = list(db.carrier_partners.find({}, {"carrier_id":1, "name":1}))
#         count = 0
#         for carrier in all_carriers:
#             carrier_id = carrier["carrier_id"]
#             if carrier_id == excluded_carrier_id:
#                 continue
#             trucks = list(db.trucks.find({
#                 "carrier_id": carrier_id, "truck_type": truck_type, "status": "unbooked"
#             }))
#             booked_truck_ids = [b["truck_id"] for b in db.booking.find({
#                 "carrier_id": carrier_id,
#                 "schedule_date": schedule_date,
#                 "booking_status": {"$in": ["Confirmed", "Pending"]}
#             },{"truck_id":1})]
#             available = [t["truck_id"] for t in trucks if t["truck_id"] not in booked_truck_ids]
#             if available:
#                 suggestions.append({
#                     "carrier_name": carrier["name"],
#                     "available_trucks": len(available),
#                     "date": schedule_date
#                 })
#                 count += 1
#             if count >= 3:
#                 break
#         return jsonify(suggestions)
#     except Exception as e:
#         logging.error(f"/suggest-alternatives error: {str(e)}")
#         return jsonify({"error": "Server error", "details": str(e)}), 500

# ========== LANE STATUS SECTION APIS ==========

@app.route("/lane-prediction", methods=["POST"])
@validate_json(schema)
def lane_prediction():
    try:
        d = request.json
        lane_id = d.get("lane_id")
        carrier_name = d.get("carrier_name")
        date = d.get("date")

        carrier = db.carrier_partners.find_one({"name": carrier_name})
        
        # Get prediction
        pred = db.predicted_lane_statuses_dl.find_one({
            "lane_id": lane_id,
            "carrier_id": carrier['carrier_id'],
            "date": date
        })

        # Get lane details
        lane = db.lanes.find_one({"lane_id": lane_id}, {"_id": 0, "origin": 1, "destination": 1, "distance": 1})

        if pred and lane:
            distance_km = lane.get("distance", 0)
            # If you have a km_to_miles utility, use it. Otherwise:
            distance_miles = round(distance_km * 0.621371, 2) if distance_km else None
            status = (
                "Balanced" if pred.get("predicted_available_truck_count_assumption", 0) == pred.get("predicted_booking_count_assumption", 0)
                else "Underbooked" if pred.get("predicted_available_truck_count_assumption", 0) > pred.get("predicted_booking_count_assumption", 0)
                else "Overbooked"
            )
            total_trucks = pred.get("predicted_available_truck_count_assumption", 0)
            booked_trucks = pred.get("predicted_booking_count_assumption", 0)
            response = {
                "origin": lane["origin"],
                "destination": lane["destination"],
                "distance_miles": distance_miles,
                "total_trucks": total_trucks,
                "available": total_trucks - booked_trucks,
                "booked": booked_trucks,
                "status": status,
                "lane_id":lane_id,
                "carrier_name": carrier_name,
                "date":date
            }
            return jsonify(response)
        else:
            return jsonify({"error": "Prediction or lane not found"}), 404

    except Exception as e:
        logging.error(f"/lane-prediction error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500


@app.route('/aggregated-lane-prediction', methods=['POST'])
@validate_json(schema)
def future_lane_prediction():
    try:
        lane_id = request.json.get("lane_id")
        date = request.json.get("date")
        
        all_preds = []
        total_trucks, total_available, total_booked = 0, 0, 0

        # Fetch lane details once
        lane = db.lanes.find_one(
            {"lane_id": lane_id},
            {"_id": 0, "origin": 1, "destination": 1}
        )
        if not lane:
            return jsonify({"error": "Lane not found"}), 404

        # Loop through all carriers
        for c in db.carrier_partners.find({}):
            pred = db.predicted_lane_statuses_dl.find_one({
                "lane_id": lane_id,
                "carrier_id": c["carrier_id"],
                "date": date
            })

            total = pred.get("predicted_available_truck_count_assumption", 0) if pred else 0
            booked = pred.get("predicted_booking_count_assumption", 0) if pred else 0
            available = total - booked

            status = (
                "Balanced" if total == booked
                else "Underbooked" if total > booked
                else "Overbooked"
            )

            all_preds.append({
                "carrier": c["name"],
                "scac_code": c["scac_code"],
                "total": total,
                "booked": booked,
                "available": available,
                "status": status
            })

            total_trucks += total
            total_available += available
            total_booked += booked

        Overall_status = (
            'Balanced' if total_trucks == total_booked
            else 'Underbooked' if total_trucks > total_booked
            else 'Overbooked'
        )

        return jsonify({
            "origin": lane["origin"],
            "destination": lane["destination"],
            "predictions": all_preds,
            "total_trucks": total_trucks,
            "total_available": total_available,
            "total_booked": total_booked,
            "Overall Status": Overall_status
        })

    except Exception as e:
        logging.error(f"/future-lane-prediction error: {str(e)}", exc_info=True)
        return jsonify({"error": "Server error", "details": str(e)}), 500



# ========== INSIGHTS SECTION APIS ==========

@app.route('/insights', methods=['GET'])
def db_insights():
    try:
        res = {
            "carrier_count": db.carrier_partners.count_documents({}),
            "truck_count": db.trucks.count_documents({}),
            "lane_count": db.lanes.count_documents({}),
            "historical_data": db.historical_lane_statuses.count_documents({})
        }
        return jsonify(res)
    except Exception as e:
        logging.error(f"/insights error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/destination-by-origin', methods=['POST'])
@validate_json(schema)
def destination_by_origin():
    try:
        origin = request.json.get("origin")
        if not origin:
            return jsonify({"error": "Missing origin"}), 400
        destinations = sorted([d["destination"] for d in db.lanes.find({"origin": origin}, {"destination":1})])
        return jsonify(destinations)
    except Exception as e:
        logging.error(f"/destination-by-origin error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route('/truck-types-count', methods=['GET'])
def truck_types_count():
    try:
        agg = db.trucks.aggregate([
            {"$group": {"_id": "$truck_type", "count": {"$sum": 1}}}
        ])
        data = [{"truck_type": row["_id"], "count": row["count"]} for row in agg]
        return jsonify(data)
    except Exception as e:
        logging.error(f"/truck-types-count error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500

# ========== ROUTE MAP SECTION API ==========

@app.route('/lane-map', methods=['POST'])
@validate_json(schema)
def lane_map_url():
    try:
        lane_id = request.json.get("lane_id")
        lane = db.lanes.find_one({"lane_id": lane_id})
        if not lane:
            return jsonify({"error": "Lane not found"}), 404

        origin, destination = lane["origin"], lane["destination"]
        origin_lat, origin_lon = get_city_coords(origin)
        dest_lat, dest_lon = get_city_coords(destination)

        if None in (origin_lat, origin_lon, dest_lat, dest_lon):
            return jsonify({"error": "Coordinates not available"}), 400

        # Construct Mapbox Directions API URL
        mapbox_url = (
            f"https://api.mapbox.com/directions/v5/mapbox/driving/"
            f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
            f"?geometries=geojson&access_token={MAPBOX_ACCESS_TOKEN}"
        )

        # Return the URL so frontend can call it directly
        return jsonify({"mapbox_url": mapbox_url})

    except Exception as e:
        logging.error(f"/lane-map-url error: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500


@app.route('/lane_map_one_origin_multi_dest', methods=['POST'])
@validate_json(schema)
def lane_map_one_origin_multi_dest():
    try:
        origin = request.json.get("origin")
        if not origin:
            return jsonify({"error": "Missing origin"}), 400

        # Lookup function for coordinates from list
        def get_coords(city_name):
            for entry in cities:
                if entry["city"].strip().title() == city_name.strip().title():
                    return entry["latitude"], entry["longitude"]
            return None, None

        # Fetch destinations from lanes table
        destinations_docs = list(
            db.lanes.find({"origin": origin.strip().title()}, {"destination": 1, "_id": 0})
        )
        destinations = [d["destination"] for d in destinations_docs]

        # Get origin coords from the list
        origin_lat, origin_lon = get_coords(origin)
        if origin_lat is None or origin_lon is None:
            return jsonify({"error": f"Coordinates not found for origin '{origin}'"}), 404

        # Get destination coords from the list
        destinations_with_coords = []
        for dest in destinations:
            dest_lat, dest_lon = get_coords(dest)
            if dest_lat is not None and dest_lon is not None:
                destinations_with_coords.append({
                    "city": dest,
                    "latitude": dest_lat,
                    "longitude": dest_lon
                })

        return jsonify({
            "origin": {
                "city": origin.strip().title(),
                "latitude": origin_lat,
                "longitude": origin_lon
            },
            "destinations": destinations_with_coords
        })

    except Exception as e:
        logging.error(f"/origin-destinations-with-coords error: {str(e)}", exc_info=True)
        return jsonify({"error": "Server error", "details": str(e)}), 500



# ========== MAIN ==========
if __name__ =='__main__':
    app.run()
    # app.run(debug=False, host="0.0.0.0", port=8888)

