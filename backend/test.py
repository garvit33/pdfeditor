import requests
url = 'http://127.0.0.1:5000/upload'
files = {"file": open("test.png", "rb")}
response = requests.post(url, files=files)


print("Status Code:", response.status_code)
print("Raw Response:", response.text)
