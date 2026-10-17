import json

#Проверка настроек
file = open("settings.json",'r',encoding="UTF-8")
json.load(file)
