from typing import List

from pydantic import BaseModel
from datetime import date

class Interval(BaseModel):
    begin: date
    end: date

class Status(BaseModel):
    # id: int
    # value: str
    name: str

    class Config:
        orm_mode = True

# class Country(BaseModel):
#     code: str
#     name: str

#     class Config:
#         orm_mode = True

class Adress(BaseModel):
    city: str = ""
    street: str = ""
    house: str = ""
    flat: str = ""

    class Config:
        orm_mode = True

# class TrainTravel(BaseModel):


class Hospital(BaseModel):
    name: str = ""
    full_name: str = ""
    address: str = ""

    class Config:
        orm_mode = True

class PatientByIIN(BaseModel):
    iin: str = "empty"

class PatientByPassNum(BaseModel):
    pass_num: str = "empty"

class Patient(BaseModel):
    first_name: str = None
    second_name: str = None
    patronymic_name: str = None
    status: Status = None
    home_address: Adress = None
    hospital: Hospital = None
    iin: str = ""
    pass_num: str = ""
    is_contacted: bool = False
    is_infected: bool = False
    is_found: bool = False
    telephone: str = ""
    created_date: date = None

    class Config:
        orm_mode = True

class PatientFrom(BaseModel):
    from_country: str = None
    patient: Patient = None