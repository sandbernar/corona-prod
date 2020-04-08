from app.main.models import Region
from app.main.flights_trains.models import FlightCode

from app import constants as c
from app import db

def get_regions(current_user):
    if current_user.region_id != None:
        return Region.query.filter_by(id=current_user.region_id).all()

    return Region.query.all()

def get_regions_choices(current_user, with_all_regions = True):
    regions = get_regions(current_user)
    choices = [ (-1, c.all_regions) ] if current_user.region_id == None and with_all_regions else []
    choices += [(r.id, r.name) for r in regions]

    return choices

def get_flight_code(flight_code_name):
    flight_code = FlightCode.query.filter_by(name=flight_code_name).first()

    if not flight_code:
        flight_code = FlightCode(name=flight_code_name)
        db.session.add(flight_code)
        db.session.commit()

    return flight_code.id