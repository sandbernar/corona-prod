import numpy as np

def generate_iin(num_iins=1):
	iins = []
	
	for i in range(num_iins):
		iin = str(9)
		for a in range(11):
			iin = iin + str(np.random.randint(10))
		iins.append(iin)

	return iins

# print("\n".join(generate_iin(12)))

from random import randrange
from datetime import timedelta, datetime

def random_date(start, end):
    """
    This function will return a random datetime between two datetime 
    objects.
    """
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)

d1 = datetime.strptime('1/1/1950 1:30 PM', '%m/%d/%Y %I:%M %p')
d2 = datetime.strptime('1/1/1992 4:50 AM', '%m/%d/%Y %I:%M %p')

# print("\n".join([random_date(d1, d2).strftime('%d.%m.%Y') for n in range(11)]))

def generate_pass_n(num_iins=1):
	iins = []
	
	for i in range(num_iins):
		iin = "N"
		for a in range(8):
			iin = iin + str(np.random.randint(10))
		iins.append(iin)

	return iins

# print("\n".join(generate_pass_n(12)))

def generate_tel(num_iins=1):
	iins = []
	prefixes = ["8707", "8701", "8702", "8777"]
	
	for i in range(num_iins):
		iin = np.random.choice(prefixes)
		for a in range(7):
			iin = iin + str(np.random.randint(10))
		iins.append(iin)

	return iins

print("\n".join(generate_tel(12)))