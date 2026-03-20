import requests
url = 'http://127.0.0.1:5000/upload'
files = {"file": open("test.png", "rb")}
response = requests.post(url, files=files)


print("Status Code:", response.status_code)
print("Raw Response:", response.text)

url2 = 'http://127.0.0.1:5000/edit'
data = {
    "x": 100,
    "y": 50,
    "w": 60,
    "h": 20,
    "new_text": "Hi"
    }
response = requests.post(url2, json = data)
print (response.json())