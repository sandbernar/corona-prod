from app.main.models import Region, Country
from app.main.flights_trains.models import FlightCode

from app import constants as c
from app import db
from datetime import datetime
from flask_babelex import _
import dateparser


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

def disable_form_fields(form, fields = []):
    readonly = {'readonly': True}

    if not fields:
        fields = [field for field in form.__dict__]

    for field in fields:
        param = getattr(form, field, None)
        if param:
            if field is not None:
                setattr(param, 'render_kw', readonly)

def parse_date(text):
    parsed_date = dateparser.parse(text)

    if parsed_date:
        return parsed_date
    else:
        raise ValueError('no valid date format found')
    

def populate_countries_select(select_input, default = None, default_state=None):
    countries = Country.query.all()

    if not select_input.choices:
        select_input.choices = []

        if default_state:
            select_input.choices += [(default_state[0], default_state[1])]

        select_input.choices += [(c.id, c.name) for c in countries]
        select_input.default = default

def yes_no(yes=True):
    return _("Да") if yes else _("Нет")

def yes_no_html(yes=True, invert_colors=False):
    yes_color = "red" if invert_colors else "green"
    no_color = "green" if invert_colors else "red"

    if yes:
        return ("<font color='{}'>{}</font>".format(yes_color, yes_no(yes)), "safe")

    return ("<font color='{}'>{}</font>".format(no_color, yes_no(yes)), "safe")