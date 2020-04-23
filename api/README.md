# API

#
## Get patient by iin
#
### Title
> get patient by iin
### URL
> /api/get_status_by_iin/
### Method
> POST
### URL Params
> None
### Header Params
> X-API-TOKEN
### Data Params
```json
{ "iin": [string] }
```
### Success Response Code
> 200
```json
{
    "status": {
        "name": [string]
    },
    "home_address": {
        "city": [string],
        "street": [string],
        "house": [string],
        "flat": [string]
    },
    "hospital": {
        "name": [string],
        "full_name": [string],
        "address": [string]
    },
    "iin": [string],
    "pass_num": [string],
    "is_contacted": [boolean],
    "is_infected": [boolean],
    "is_found": [boolean],
    "telephone": [string]

}
```
### Error Response 
> Code: 400
```json
{
    "ErrorCode": "invalid_request",
    "Error": "Invalid Authorization Code"
}
```

> Code: 400
```json
{
    "ErrorCode": "invalid_request",
    "Error": "The request is missing a required header : X-API-TOKEN"
}
```

> Code: 404
```json
{
    "detail": "Patient not found"
}
```

### Sample Call      
```bash
curl -v -X POST "http://demo.crm.alem.school/api/get_status_by_iin/" -H "X-API-TOKEN: ${API_TOKEN}" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"iin\":\"1212\"}"
```

#
## Get patient by password number
#
### Title
> get patient by password number
### URL
> /api/get_status_by_pass_num/
### Method
> POST
### URL Params
> None
### Header Params
> X-API-TOKEN
### Data Params
```json
{ "pass_num": [string] }
```
### Success Response Code
> 200
```json
{
    "status": {
        "name": [string]
    },
    "home_address": {
        "city": [string],
        "street": [string],
        "house": [string],
        "flat": [string]
    },
    "hospital": {
        "name": [string],
        "full_name": [string],
        "address": [string]
    },
    "iin": [string],
    "pass_num": [string],
    "is_contacted": [boolean],
    "is_infected": [boolean],
    "is_found": [boolean],
    "telephone": [string]
}
```
### Error Response 
> Code: 400
```json
{
    "ErrorCode": "invalid_request",
    "Error": "Invalid Authorization Code"
}
```

> Code: 400
```json
{
    "ErrorCode": "invalid_request",
    "Error": "The request is missing a required header : X-API-TOKEN"
}
```

> Code: 404
```json
{
    "detail": "Patient not found"
}
```

### Sample Call      
```bash
curl -v -X POST "http://demo.crm.alem.school/api/get_status_by_pass_num/" -H "X-API-TOKEN: ${API_TOKEN}" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"pass_num\":\"1213\"}"
```

#
## Get patient within interval
#
### Title
> get patients
### URL
> /api/get_patients_within_interval/
### Method
> POST
### URL Params
> None
### Header Params
> X-API-TOKEN
### Data Params
```json
{ 
    "behin": [datetime YYYY-MM-DD],
    "end": [datetime YYYY-MM-DD],
}
```
### Success Response Code
> 200
```json
    [
        {
            "status": {
                "name": [string]
            },
            "home_address": {
                "city": [string],
                "street": [string],
                "house": [string],
                "flat": [string]
            },
            "hospital": {
                "name": [string],
                "full_name": [string],
                "address": [string]
            },
            "iin": [string],
            "pass_num": [string],
            "is_contacted": [boolean],
            "is_infected": [boolean],
            "is_found": [boolean],
            "telephone": [string]
        }
    ]
```
### Error Response 
> Code: 400
```json
{
    "ErrorCode": "invalid_request",
    "Error": "Invalid Authorization Code"
}
```

> Code: 400
```json
{
    "ErrorCode": "invalid_request",
    "Error": "The request is missing a required header : X-API-TOKEN"
}
```

### Sample Call      
```bash
curl -X POST "http://demo.crm.alem.school/api/get_patients_within_interval/" -H "X-API-TOKEN: ${API_TOKEN}" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"begin\":\"2019-02-21\",\"end\":\"2021-02-20\"}"
```