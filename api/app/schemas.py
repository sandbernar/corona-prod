from typing import List, Optional

from pydantic import BaseModel
from datetime import date

class Interval(BaseModel):
    begin: date
    end: date
    page: int

class Status(BaseModel):
    # id: int
    # value: str
    name: Optional[str] = None

    class Config:
        orm_mode = True

# class Country(BaseModel):
#     code: str
#     name: str

#     class Config:
#         orm_mode = True

class Adress(BaseModel):
    city: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = None
    flat: Optional[str] = None

    class Config:
        orm_mode = True

# class TrainTravel(BaseModel):


class Hospital(BaseModel):
    name: Optional[str] = ""
    full_name: Optional[str] = ""
    address: Optional[str] = ""

    class Config:
        orm_mode = True

class PatientByIIN(BaseModel):
    iin: str

class PatientByPassNum(BaseModel):
    pass_num: str

class Patient(BaseModel):
    first_name: Optional[str] = None
    second_name: Optional[str] = None
    patronymic_name: Optional[str] = None
    status: Optional[Status] = None
    home_address: Optional[Adress] = None
    hospital: Optional[Hospital] = None
    iin: Optional[str] = None
    pass_num: Optional[str] = None
    is_contacted: Optional[bool] = False
    is_infected: Optional[bool] = False
    is_found: Optional[bool] = False
    telephone: Optional[str] = None
    created_date: Optional[date] = None

    class Config:
        orm_mode = True

class PatientFrom(BaseModel):
    from_country: Optional[str] = None
    to_region: Optional[str] = None
    patient: Optional[Patient] = None

class RegionId(BaseModel):
    region_id: int

class Region(BaseModel):
    id: int
    name: str

class RegionStats(BaseModel):
	infected: int
	contacted: int

class RegionStatsFrom(BaseModel):
    region: Optional[str] = None
    id: Optional[int] = None
    stats: Optional[RegionStats] = None