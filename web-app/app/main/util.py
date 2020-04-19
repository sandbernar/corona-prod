from app.main.models import Region
from app.main.flights_trains.models import FlightCode

from app import constants as c
from app import db
from datetime import datetime

def get_regions(current_user):
    # if current_user.region_id != None:
        # return Region.query.filter_by(id=current_user.region_id).all()

    return Region.query.all()

def get_regions_choices(current_user, with_all_regions = True):
    regions = get_regions(current_user)
    choices = []
    
    if with_all_regions:
        # if current_user.region_id == None or current_user.is_admin:
        choices += [ (-1, c.all_regions) ]

    choices += [(r.id, r.name) for r in regions]

    return choices

def get_flight_code(flight_code_name):
    flight_code = FlightCode.query.filter_by(name=flight_code_name).first()

    if not flight_code:
        flight_code = FlightCode(name=flight_code_name)
        db.session.add(flight_code)
        db.session.commit()

    return flight_code.id

def populate_form(form, attrs, prefix = ''):
    for k in attrs:
        param = getattr(form, prefix + k, None)
        if param:
            if attrs[k] is not None:
                value = attrs[k]
                if type(value) == bool:
                    value = int(value)
                setattr(param, 'default', value)  

def disable_form_fields(form, fields):
    readonly = {'readonly': True}

    for field in fields:
        param = getattr(form, field, None)
        if param:
            if field is not None:
                setattr(param, 'render_kw', readonly)

def parse_date(text):
    for date_format in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            pass
    raise ValueError('no valid date format found')