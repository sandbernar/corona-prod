import pandas as pd
import numpy as np
from random import randrange
from datetime import timedelta
from datetime import datetime
import random
import string
from faker import Faker

countries = ["Казахстан", "Россия", "Италия", "Германия", "Китай", "США"]
regions = ["Алматы", "Нур-Султан", "Шымкент"]
choices = ["да", "нет"]
hospitals = ["Многопрофильный медицинский центр", "домашний карантин", "стационар", "транзит", "вылет в швейцарию", "Городская инфекционная больница"]
addresses = ["Сарайшык", "Кунаева", "Сейфуллина", "Рыскулова", "Абая", "Жангельдина", "Панфилова", "Торекулова", "Желтоксан", "Сыганак"]

def random_date(start, end):
    """
    This function will return a random datetime between two datetime 
    objects.
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)

def generate_fake_csv():
    columns=["Дата въезда","рейс", "ФИО", "ИИН", "Дата рождения", "Номер паспорта", "Гражданство", "Номер мобильного телефона", "Место и сроки пребывания в последние 14 дней до прибытия в Казахстан (укажите страну, область, штат и т.д.)", "регион", "Место жительство, либо предпологаемое место проживания", "Место работы", "Найден (да/нет)","Госпитализирован (да/нет)","Место госпитализации"]
    df = pd.DataFrame(columns=columns)
    
    d1 = datetime.strptime('1/03/2020 1:30 PM', '%d/%m/%Y %I:%M %p')
    d2 = datetime.strptime('26/03/2020 4:50 AM', '%d/%m/%Y %I:%M %p')

    travel_date = random_date(d1, d2)
    
    first_char = random.choice(string.ascii_letters).upper()
    second_char = random.choice(string.ascii_letters).upper()

    flight_code = "{}{} {}".format(first_char, second_char, np.random.randint(300))
    
    rows_num = np.random.randint(70, 90)
    fake = Faker(['ru_RU'])
    
    for i in range(rows_num):
        profile = fake.profile()

        name = profile["name"]
        iin = profile["ssn"]
        birthdate = profile["birthdate"]
        pass_num = "N{}".format(fake.ssn()[:8])
        citizenship = random.choice(countries)
        phone_number = fake.phone_number().replace(" ", "")       
        visited_country = random.choice(countries)
        region = random.choice(regions)
        address = "{}, {}".format(random.choice(addresses), np.random.randint(160))
        job = profile["job"]        
        
        is_found = None
        
        in_hospital = random.choice(choices)
        if in_hospital == "да":
            is_found = "да"
        else:
            is_found = random.choice(choices)
        
        hospital = "" if in_hospital == "нет" else random.choice(hospitals)
        
        new_row = pd.DataFrame([[travel_date, flight_code, name, iin, birthdate,
                               pass_num, citizenship, phone_number,
                               visited_country, region, address, job, is_found,
                               in_hospital, hospital]], columns=columns)
        
        df = df.append(new_row)
        
        df.to_excel("{}.xlsx".format(flight_code), index=False)

generate_fake_csv()