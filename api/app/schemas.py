from typing import List

from pydantic import BaseModel

class Status(BaseModel):
    # id: int
    # value: str
    name: str

    class Config:
        orm_mode = True

class Adress(BaseModel):
    

class PatientBase(BaseModel):
    pass

class PatientByIIN(PatientBase):
    iin: str = "empty"

class PatientByPassNum(PatientBase):
    pass_num: str = "empty"

class Patient(PatientBase):
    status: Status
    adress: Adress
    iin: str
    pass_num: str

    class Config:
        orm_mode = True