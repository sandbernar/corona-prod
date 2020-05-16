# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

import datetime

from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey, JSON, DateTime
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property
from sqlalchemy import select, func, case, and_, or_

from app import db
from app import constants as c
from app.login.models import User
from app.main.models import Country, Address, VisitedCountry, JobCategory
from app.login.util import hash_pass

class State(db.Model):
    """
    State class represents Patient state:
    * infected
    * dead
    * healthy
    """

    __tablename__ = 'State'
    id = Column(Integer, primary_key=True)
    value = Column(String, nullable=True)
    name = Column(String, nullable=False)

class PatientState(db.Model):
    """
    PatientState represents many-to-many relationship between Patient and State tables.
    Table includes:
    * created_at: creation datetime
    * detection_date: datetime of detection
    * comment: comment on state
    """
    __tablename__ = 'PatientState'

    id = Column(Integer, primary_key=True, index=True)
    state_id = Column(Integer, nullable=False)
    patient_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    detection_date = Column(DateTime, default=datetime.datetime.utcnow)
    comment = Column(String, nullable=True)
    attrs = Column(JSON, default={})

class Patient(db.Model):

    __tablename__ = 'Patient'

    id = Column(Integer, primary_key=True)
    attrs = Column(JSON, unique=False)
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('User.id'))
    created_by = db.relationship('User')
    travel_type_id = Column(Integer, ForeignKey('TravelType.id'), nullable=True, default=None)
    travel_type = db.relationship('TravelType')
    travel_id = Column(Integer, nullable=True, default=None, unique=False) #obsolete
    first_name = Column(String, unique=False)
    second_name = Column(String, unique=False)
    patronymic_name = Column(String, unique=False, nullable=True)

    # False - male, True - female, None - unknown
    gender = Column(Boolean, nullable=True, default=None)
    dob = Column(Date, nullable=False)
    iin = Column(String, nullable=True, default=None)
    citizenship_id = Column(Integer, ForeignKey('Country.id'))
    citizenship = db.relationship('Country', foreign_keys=[citizenship_id])
    pass_num = Column(String, unique=False, nullable=True, default=None)
    country_of_residence_id = Column(Integer, ForeignKey('Country.id'), nullable=True)
    country_of_residence = db.relationship('Country', foreign_keys=[country_of_residence_id])
    home_address_id = Column(Integer, ForeignKey('Address.id'), nullable=False)
    home_address = db.relationship('Address', 
                                    foreign_keys=[home_address_id], 
                                    cascade="all,delete", 
                                    backref="Patient")
    telephone = Column(String, nullable=True, default=None)
    email = Column(String, nullable=True, default=None)
    region_id = Column(Integer, ForeignKey('Region.id'))
    region = db.relationship('Region')
    hospital_id = Column(Integer, ForeignKey('Hospital.id'), nullable=True, default=None)
    hospital = db.relationship('Hospital')
    job = Column(String, nullable=True, default=None)
    job_position = Column(String, nullable=True, default=None)
    job_address_id = Column(Integer, ForeignKey('Address.id'), nullable=True, default=None)
    job_address = db.relationship('Address', 
                                    foreign_keys=[job_address_id],
                                    cascade="all, delete-orphan",
                                    single_parent=True)
    job = Column(String, nullable=True, default=None)
    job_position = Column(String, nullable=True, default=None)
    job_address_id = Column(Integer, ForeignKey('Address.id'), nullable=True, default=None)
    job_address = db.relationship('Address', foreign_keys=[
                                  job_address_id], cascade="all, delete-orphan", single_parent=True)
    
    job_category_id = Column(Integer, ForeignKey('JobCategory.id'), nullable=True, default=None)
    job_category = db.relationship('JobCategory')
    
    is_dead = Column(Boolean, default=False)
    in_hospital = Column(Boolean, default=False)
    is_home = Column(Boolean, default=False)
    is_infected = Column(Boolean, default=False)
    is_healthy = Column(Boolean, default=False)
    is_found = Column(Boolean, default=False)


    # DEPRECATED
    status_id = Column(Integer, ForeignKey('PatientStatus.id'))
    status = db.relationship('PatientStatus')
    is_contacted_person = Column(Boolean, unique=False)
    is_contacted = Column(Boolean, unique=False, default=False)


    # """
    # Infected column_property
    # """
    # infected_state_count = column_property(
    #     select([func.count(PatientState.id)]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_infec[0]).limit(1))
    # )

    # last_infected_state_id = column_property(
    #     select([PatientState.id]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_infec[0]).limit(1)).\
    #         order_by(PatientState.detection_date.desc()).limit(1)
    # )

    # last_infected_state_dd = column_property(
    #     select([PatientState.detection_date]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_infec[0]).limit(1)).\
    #         order_by(PatientState.detection_date.desc()).limit(1)
    # )

    # """
    # Found column_property
    # """

    # found_state_count = column_property(
    #     select([func.count(PatientState.id)]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_found[0]).limit(1))
    # )

    # """
    # Hospitalised column_properties
    # """
    # hosp_state_count = column_property(
    #     select([func.count(PatientState.id)]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_hosp[0]).limit(1))
    # )

    # last_hosp_state_id = column_property(
    #     select([PatientState.id]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_hosp[0]).limit(1)).\
    #         order_by(PatientState.detection_date.desc()).limit(1)
    # )

    # last_hosp_state_dd = column_property(
    #     select([PatientState.detection_date]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_hosp[0]).limit(1)).\
    #         order_by(PatientState.detection_date.desc()).limit(1)
    # )

    # """
    # Healthy (recovered) column_properties
    # """
    # healty_state_count = column_property(
    #     select([func.count(PatientState.id)]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_healthy[0]).limit(1))
    # )

    # last_healty_state_id = column_property(
    #     select([PatientState.id]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_healthy[0]).limit(1)).\
    #         order_by(PatientState.detection_date.desc()).limit(1)
    # )

    # last_healty_state_dd = column_property(
    #     select([PatientState.detection_date]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_healthy[0]).limit(1)).\
    #         order_by(PatientState.detection_date.desc()).limit(1)
    # )

    # """
    # Is home (home carantine) column_properties
    # """
    # home_state_count = column_property(
    #     select([func.count(PatientState.id)]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_is_home[0]).limit(1))
    # )

    # last_home_state_id = column_property(
    #     select([PatientState.id]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_is_home[0]).limit(1)).\
    #         order_by(PatientState.detection_date.desc()).limit(1)
    # )

    # last_home_state_dd = column_property(
    #     select([PatientState.detection_date]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_is_home[0]).limit(1)).\
    #         order_by(PatientState.detection_date.desc()).limit(1)
    # )

    # """
    # Dead column_property
    # """
    # dead_state_count = column_property(
    #     select([func.count(PatientState.id)]).\
    #         where(PatientState.patient_id==id).\
    #         where(PatientState.state_id == select([State.id]).where(State.value == c.state_dead[0]).limit(1))
    # )

    # infected, dead, healthy
    # states = db.relationship("State", secondary=lambda: PatientState.__table__,
    #                          backref=db.backref("patients"))
    @hybrid_property
    def states(self):
        results = PatientState.query.filter_by(patient_id=self.id).all()
        results = sorted(results, key=lambda k: (k.detection_date, k.id), reverse=True)
        for i in range(len(results)):
            state = State.query.filter_by(id=results[i].state_id).first()
            results[i].name = state.name
            results[i].value = state.value
            results[i].formatted_detection_date = datetime.datetime.strftime(results[i].detection_date, "%d.%m.%Y")
            results[i].formatted_comment = results[i].comment
            if results[i].comment is None:
                results[i].formatted_comment = "Нет деталей"
        return results
    
    def updateState(self, patient_state: PatientState):
        if self.id is None:
            return False
        state = State.query.filter_by(id=patient_state.state_id).first()
        if not state:
            return False
        patient_state.value = state.value
        patient_state.name = state.name
        if patient_state.detection_date == "":
            patient_state.detection_date = datetime.datetime.now()
        else:
            patient_state.detection_date = datetime.datetime.strptime(patient_state.detection_date, "%Y-%m-%d")
        states = [st for st in self.states if st.id != patient_state.id]
        states.append(patient_state)
        states = sorted(states, key=lambda k: (k.detection_date, k.id))
        patientStates = [(st.value, st.name) for st in states]
        graph = c.GraphState()
        for st in patientStates:
            result = graph.add(st)
            if result == False:
                return False
        db.session.add(patient_state)
        db.session.commit()
        return True

    def deleteState(self, patient_state_id: int):
        if self.id is None:
            return False
        deletePatientState = PatientState.query.filter_by(id=patient_state_id).first()
        if deletePatientState is None:
            return False
        states = self.states
        states = sorted(states, key=lambda k: (k.detection_date, k.id))
        patientStates = [(st.value, st.name) for st in states if st.id != deletePatientState.id]
        graph = c.GraphState()
        for st in patientStates:
            result = graph.add(st)
            if result == False:
                return False
        db.session.delete(deletePatientState)
        db.session.commit()
        return True

    def addState(self, state: State, detection_date=None, comment=None, attrs=None):
        if self.id is None:
            return False
        tmpState = PatientState(patient_id=self.id, state_id=state.id)
        tmpState.value = state.value
        tmpState.name = state.name
        tmpState.id = 9999999999
        tmpState.detection_date = datetime.datetime.now()
        if detection_date is not None and detection_date != "":
            tmpState.detection_date = datetime.datetime.strptime(detection_date, "%Y-%m-%d")
        states = self.states
        states.append(tmpState)
        states = sorted(states, key=lambda k: (k.detection_date, k.id))
        patientStates = [(st.value, st.name) for st in states]

        print(patientStates)
        graph = c.GraphState()
        for st in patientStates:
            result = graph.add(st)
            if result == False:
                return False

        patientState = PatientState(patient_id=self.id, state_id=state.id)
        if detection_date is not None:
            patientState.detection_date = tmpState.detection_date
        if comment is not None:
            patientState.comment = comment
        if attrs is not None:
            patientState.attrs = attrs
        db.session.add(patientState)
        db.session.commit()
        return True

    # @hybrid_property
    # def in_hospital(self):
    #     if self.is_dead or self.hosp_state_count == 0:
    #         return False
    #     if self.home_state_count > 0:
    #         if self.last_home_state_dd > self.last_hosp_state_dd:
    #             return False
    #         if self.last_home_state_dd == self.last_hosp_state_dd \
    #             and self.last_home_state_id > self.last_hosp_state_id:
    #             return False
    #     if self.healty_state_count > 0:
    #         if self.last_healty_state_dd > self.last_hosp_state_dd:
    #             return False
    #         if self.last_healty_state_dd == self.last_hosp_state_dd \
    #             and self.last_healty_state_id > self.last_hosp_state_id:
    #             return False
    #     return self.hosp_state_count > 0

    # @in_hospital.expression
    # def in_hospital(cls):
    #     # если последний in_hospital.detection_date > is_home.detection.date OR in_hospital.detection_date > is_healthy.detection_date
    #     return case([
    #         (or_(cls.dead_state_count > 0, cls.hosp_state_count == 0), False),
    #         (and_(cls.home_state_count > 0, cls.last_home_state_dd > cls.last_hosp_state_dd), False),
    #         (and_(cls.home_state_count > 0, and_(cls.last_home_state_dd == cls.last_hosp_state_dd, cls.last_home_state_id > cls.last_hosp_state_id)), False),
    #         (and_(cls.healty_state_count > 0, cls.last_healty_state_dd > cls.last_hosp_state_dd), False),
    #         (and_(cls.healty_state_count > 0, and_(cls.last_healty_state_dd == cls.last_hosp_state_dd, cls.last_healty_state_id > cls.last_hosp_state_id)), False)
    #     ], else_=cls.hosp_state_count > 0)

    # is_found = Column(Boolean, unique=False, default=False)
    # @hybrid_property
    # def is_found(self):
    #     return self.found_state_count > 0

    # @is_found.expression
    # def is_found(cls):
    #     return cls.found_state_count > 0
    
    # TODO
    # @is_found.setter
    # def is_found(self, value):
    #     if value == True:
    #         state = State.query.filter_by(value=c.state_found[0]).first()
    #         self.addState(state)

    # is_infected = Column(Boolean, unique=False, default=False)
    # @hybrid_property
    # def is_infected(self):
    #     if self.is_dead or self.infected_state_count == 0:
    #         return False
    #     if self.healty_state_count > 0:
    #         if self.last_healty_state_dd > self.last_infected_state_dd:
    #             return False
    #         if self.last_healty_state_dd == self.last_infected_state_dd \
    #             and self.last_healty_state_id > self.last_infected_state_id:
    #             return False
    #     return self.infected_state_count > 0
    
    # @is_infected.expression
    # def is_infected(cls):
    #     return case([
    #         (or_(cls.dead_state_count > 0, cls.infected_state_count == 0), False),
    #         (and_(cls.healty_state_count > 0, cls.last_healty_state_dd > cls.last_infected_state_dd), False),
    #         (and_(cls.healty_state_count > 0, 
    #         and_(cls.last_healty_state_dd == cls.last_infected_state_dd, 
    #             cls.last_healty_state_id > cls.last_infected_state_id)), False)
    #     ], else_=cls.infected_state_count > 0)
    
    # TODO
    # @is_infected.setter
    # def is_infected(self, value):
    #     if value == True:
    #         state = State.query.filter_by(value=c.state_infec[0]).first()
    #         self.addState(state)
    
    # @hybrid_property
    # def is_home(self):
    #     # если последний is_home.detection_date > in_hospital.detection.date OR is_home.detection_date > is_healthy.detection_date
    #     if self.is_dead or self.home_state_count == 0:
    #         return False
    #     if self.hosp_state_count > 0:
    #         if self.last_hosp_state_dd > self.last_home_state_dd:
    #             return False
    #         if self.last_hosp_state_dd == self.last_home_state_dd \
    #             and self.last_hosp_state_id > self.last_home_state_id:
    #             return False
    #     if self.healty_state_count > 0:
    #         if self.last_healty_state_dd > self.last_home_state_dd:
    #             return False
    #         if self.last_healty_state_dd == self.last_home_state_dd \
    #             and self.last_healty_state_id > self.last_home_state_id:
    #             return False
    #     return self.home_state_count > 0
    
    # @is_home.expression
    # def is_home(cls):
    #     return case([
    #         (or_(cls.dead_state_count > 0, cls.home_state_count == 0), False),
    #         (and_(cls.hosp_state_count > 0, cls.last_hosp_state_dd > cls.last_home_state_dd), False),
    #         (and_(cls.hosp_state_count > 0, and_(cls.last_hosp_state_dd == cls.last_home_state_dd, cls.last_hosp_state_id > cls.last_home_state_id)), False),
    #         (and_(cls.healty_state_count > 0, cls.last_healty_state_dd > cls.last_home_state_dd), False),
    #         (and_(cls.healty_state_count > 0, and_(cls.last_healty_state_dd == cls.last_home_state_dd, cls.last_healty_state_id > cls.last_home_state_id)), False)
    #     ], else_=cls.home_state_count > 0)
    
    # @hybrid_property
    # def healthy(self):
    #     if self.is_dead or self.healty_state_count == 0:
    #         return False
    #     if self.in_hospital:
    #         return False
    #     if self.is_home:
    #         return False
    #     return self.healty_state_count > 0
    
    # @healthy.expression
    # def healthy(cls):
    #     return case([
    #         (or_(cls.dead_state_count > 0, cls.healty_state_count == 0), False),
    #         (cls.in_hospital, False),
    #         (cls.is_home, False),
    #     ], else_=cls.healty_state_count > 0)
    
    # @hybrid_property
    # def is_dead(self):
    #     return self.dead_state_count > 0

    def __init__(self, **kwargs):
        for hybrid_property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]

            setattr(self, hybrid_property, value)

    def __repr__(self):
        return "{} {} {}".format(str(self.second_name), str(self.first_name), str(self.patronymic_name))

    @hybrid_property
    def serialize(self):
        """Return object data in easily serializable format"""
        color = "green"
        if self.is_infected == True:	
            color = "red"
        return {
            "type": "Feature",
            "id": self.id,
            "geometry": {"type": "Point", "coordinates": [self.home_address.lat, self.home_address.lng]},
            "properties": {
                    "balloonContent": "идет загрузка...",
                    "clusterCaption": "идет загрузка...",
                    # "hintContent": "Текст подсказки"
            },
            "options": {
                "preset": "islands#icon",
                "iconColor": color
            }
        }

    def get_created_date(self):
        sql = "select * from logging.t_history WHERE tabname='{}' \
                AND new_val->>'id'='{}' AND operation='INSERT';".format(self.__tablename__, self.id)
        result = db.engine.execute(sql)
        created_date = result.fetchone()[1]

        return created_date

class ContactedPersons(db.Model):
    __tablename__ = 'ContactedPersons'

    id = Column(Integer, primary_key=True)
    infected_patient_id = Column(Integer, ForeignKey('Patient.id', ondelete="CASCADE"))
    infected_patient = db.relationship('Patient', foreign_keys=[infected_patient_id],
                                       backref=db.backref('infected_patient', passive_deletes=True))
    contacted_patient_id = Column(Integer, ForeignKey('Patient.id'))
    contacted_patient = db.relationship('Patient', foreign_keys=[contacted_patient_id])

    attrs = Column(JSON, unique=False)

    def __init__(self, **kwargs):
        for hybrid_property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]
            setattr(self, hybrid_property, value)

    def __repr__(self):
        return str(self.id)

    @hybrid_property
    def created_date(self):
        sql = "select * from logging.t_history WHERE tabname='ContactedPersons' \
                AND new_val->>'id'='{}' AND operation='INSERT';".format(self.id)
        result = db.engine.execute(sql)
        created_date = result.fetchone()[1]

        return created_date

    def added_in_n_hours(self, hours = 2):
        infected_created_date = self.infected_patient.get_created_date()

        return self.created_date - infected_created_date < datetime.timedelta(hours=hours)

class PatientStatus(db.Model):
    """
    DEPRECATED
    PatientStatus class for representing Patient's current status:
    1 | no_status   | Нет Статуса
    2 | in_hospital | Госпитализирован
    3 | is_home     | Домашний Карантин
    4 | is_transit  | Транзит
    """

    __tablename__ = 'PatientStatus'

    id = Column(Integer, primary_key=True)
    value = Column(String, unique=True)
    name = Column(String, unique=True)

    def __init__(self, **kwargs):
        for hybrid_property, value in kwargs.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                value = value[0]

            setattr(self, hybrid_property, value)

    def __repr__(self):
        return str(self.name)
