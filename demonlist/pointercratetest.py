import requests
limit = 100
after = 0
response = requests.get(f"https://pointercrate.com/api/v2/demons/listed")#/?limit=${limit}&after=${after}")
data = response.json()
for i in data:
    print(i, end='\n\n')