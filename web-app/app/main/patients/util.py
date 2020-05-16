from app.main.patients.models import Patient
from nltk.metrics.distance import edit_distance


def measure_patient_similarity(patient1, patient2):
	similarity = 0
	full_name1 = str(patient1).lower()
	full_name2 = str(patient2).lower()

	if full_name1 == full_name2:
		similarity = 1
	elif patient1.iin != "" and patient2.iin != "":
		if patient1.iin == patient2.iin:
			similarity = 1
		elif patient1.iin in patient2.iin:
			similarity = 1
		elif patient2.iin in patient1.iin:
			similarity = 1
	else:
		edit_sim = 1 - edit_distance(full_name1, full_name2)/max(len(full_name1), len(full_name2))
		similarity = edit_sim

	return similarity