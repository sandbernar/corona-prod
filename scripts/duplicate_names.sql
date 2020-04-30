select 
    id, 
    first_name, 
    second_name,
    iin,
    dob,
    (SELECT name FROM "Region" WHERE "Region".id=ou.region_id) AS region,
    (SELECT name FROM "Country" WHERE "Country".id=(SELECT country_id FROM "Address" WHERE "Address".id=ou.home_address_id LIMIT 1)) AS home_country,
	(SELECT state FROM "Address" WHERE "Address".id=ou.home_address_id LIMIT 1) AS home_state,
	(SELECT county FROM "Address" WHERE "Address".id=ou.home_address_id LIMIT 1) AS home_county,
	(SELECT city FROM "Address" WHERE "Address".id=ou.home_address_id LIMIT 1) AS home_city,
	(SELECT street FROM "Address" WHERE "Address".id=ou.home_address_id LIMIT 1) AS home_street,
	(SELECT house FROM "Address" WHERE "Address".id=ou.home_address_id LIMIT 1) AS home_house,
	(SELECT flat FROM "Address" WHERE "Address".id=ou.home_address_id LIMIT 1) AS home_flat,
	(SELECT building FROM "Address" WHERE "Address".id=ou.home_address_id LIMIT 1) AS home_building
from "Patient" ou where 
    (ou.travel_type_id=6 OR ou.travel_type_id=7) AND 
    (select 
        count(*) 
    from "Patient" inr where 
        inr.first_name ILIKE ou.first_name AND 
        inr.second_name ILIKE ou.second_name) > 1;