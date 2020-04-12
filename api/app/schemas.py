from typing import List

from pydantic import BaseModel

class Status(BaseModel):
    # id: int
    # value: str
    name: str

    class Config:
        orm_mode = True

class Adress(BaseModel):
    city: str
    street: str
    house: str
    flat: str

    class Config:
        orm_mode = True

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
    status: Status
    home_address: Adress
    hospital: Hospital = None
    iin: str
    pass_num: str
    is_contacted: bool
    is_infected: bool
    is_found: bool

    class Config:
        orm_mode = True