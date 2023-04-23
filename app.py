from flask import Flask, render_template, request, redirect, url_for, flash, make_response, Blueprint
from replit import Database
from argon2 import PasswordHasher
from passlib.hash import sha256_crypt
import openai
import ee
import requests
from PIL import Image
import os
import pandas as pd
import warnings
import autogluon
warnings.filterwarnings('ignore')
from autogluon.multimodal import MultiModalPredictor
from autogluon.core.utils.loaders import load_pd
from autogluon.tabular import TabularDataset
from sklearn.metrics import accuracy_score
import uuid

openai.api_key = "Key goes here" # Remove key in production

ph = PasswordHasher()

db = Database(db_url="https://kv.replit.com/v0/eyJhbGciOiJIUzUxMiIsImlzcyI6ImNvbm1hbiIsImtpZCI6InByb2Q6MSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJjb25tYW4iLCJleHAiOjE2ODIzNTE5MzQsImlhdCI6MTY4MjI0MDMzNCwiZGF0YWJhc2VfaWQiOiIwMWU2YzIwZS03ZGZlLTQwNWYtYTQ5OS1kYjBjY2NkNTMxYTEiLCJ1c2VyIjoiQzBEM1cxWiIsInNsdWciOiJGaXJlV2F0Y2gtREIifQ.938tF2WOvIUmoTa_s5nkYXioXTbDJpMAKSAD91_dy_STo9gkB835Es8MJczRZOZKe_FyJjl9faBPAVjV-lrFQQ")

app = Flask(__name__)

@app.route('/chat', methods=['POST', 'GET'])
def chat():
    global percent
    percent = request.json['percent']

@app.route("/chatbot", methods=['POST', 'GET'])
def chatbot():

  loggedIn = request.cookies.get("loggedIn")
  username = request.cookies.get("username")
  session = request.cookies.get("session")
  perms = 'none'
  if loggedIn == "true":
    if username != None and username in db.keys():
      if ph.verify(session, username) == True:
        perms = db[username+"stat"]

  output1 = openai.Completion.create(
            engine="text-davinci-002",
            prompt=f'Based off a calculated {rounded_proba}% probability of wildfire (percentage can have decimals), provide me with wildfire prevention strategies. Start your answer with "The likelihood of a wildfire occuring in your area is" and the percentage given. Your answer should be personal and direct. Use sentences only, NO dashes or other special characters or bullet points.',
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.7,
            )

  for output2 in output1.choices:
      language = 'en'
      output=output2.text.strip()

  if request.method == "POST":
    input = request.form.get("textinput")

    output1 = openai.Completion.create(
            engine="text-davinci-002",
            prompt=f"Based off the previous question and answer, answer this: {input}",
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.7,
            )

  for output2 in output1.choices:
      language = 'en'
      output=output2.text.strip()
  
  return render_template("chatbot.html", output=output, loggedIn=loggedIn, perms = perms)

@app.route("/getinfo", methods=["GET", "POST"])
def getinfo():
  global address, latitude, longitude
  data = request.json
  address = data['address']
  latitude = int(data['latitude'])
  longitude = int(data['longitude'])
  print(latitude, longitude)

  ee.Initialize()

  # Define the coordinates and altitude of the satellite image
  lat = latitude
  lon = longitude
  alt = 1880  # in meters

  # Create a geometry object from the coordinates
  point = ee.Geometry.Point(lon, lat)

  # Create an image collection object of Sentinel-2 surface reflectance data
  collection = ee.ImageCollection('COPERNICUS/S2_SR')

  # Filter the collection to get only images acquired during daytime
  collection = collection.filter(ee.Filter.calendarRange(10, 18, 'hour'))

  # Filter the collection to get a single image at the given point and altitude
  image = collection.filterBounds(point).filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10).sort('CLOUDY_PIXEL_PERCENTAGE').first().resample('bicubic').reproject(crs='EPSG:4326', scale=10).clip(point.buffer(alt).bounds().buffer(10000))

  # Get the URL of the image
  url = image.getThumbUrl({
      'min': 0,
      'max': 3000,
      'dimensions': '350',
      'region': point.buffer(alt).bounds().getInfo()['coordinates']
  })

  # Download the image and save it locally
  response = requests.get(url)
  with open('img.jpg', 'wb') as f:
      f.write(response.content)

  image_path = './wildfiremodelnoinput/img.jpg'

  model_path = "./wildfiremodelnoinput/model/new_model"
  predictor = MultiModalPredictor.load(model_path)

  if __name__ == '__main__':
      global predictions, rounded_proba
      predictions = predictor.predict({'image': [image_path]})
      proba = predictor.predict_proba({'image': [image_path]})
      print(predictions[-1])
      rounded_proba = round(proba[-1][-1]*100, 1)
      print(rounded_proba)
      
  return redirect("/chatbot")


@app.route("/search")
def search():
  loggedIn = request.cookies.get("loggedIn")
  username = request.cookies.get("username")
  session = request.cookies.get("session")
  perms = 'none'
  if loggedIn == "true":
    if username != None and username in db.keys():
      if ph.verify(session, username) == True:
        perms = db[username+"stat"]
  return render_template("search.html", loggedIn=loggedIn, perms = perms)

@app.route("/")
def welcome():
  loggedIn = request.cookies.get("loggedIn")
  username = request.cookies.get("username")
  session = request.cookies.get("session")
  perms = 'none'
  if loggedIn == "true":
    if username != None and username in db.keys():
      if ph.verify(session, username) == True:
        perms = db[username+"stat"]
  return render_template("index.html", loggedIn=loggedIn, perms = perms)


@app.route("/settings", methods=["GET", "POST"])
def settings():

  loggedIn = request.cookies.get("loggedIn")
  username = request.cookies.get("username")
  session = request.cookies.get("session")
  perms = 'none'
  if loggedIn == "true":
    if username != None and username in db.keys():
      if ph.verify(session, username) == True:
        perms = db[username+"stat"]
  
  if request.method == "POST":    
    currpass = request.form.get("currpass")
    newpass = request.form.get("newpass")
    repass = request.form.get("repass")
    
    if sha256_crypt.verify(currpass, db[username]) == True:
      if newpass == repass:
        db[username] = sha256_crypt.encrypt(newpass)
        print(db[username])

  if loggedIn == "true":
    if username != None and username in db.keys():
      if ph.verify(session, username) == True:
        return render_template("settings.html", loggedIn = loggedIn, username = username, session = session, perms = perms)
    else:
      return redirect("/logout")
  else:
    return render_template("notloggedin.html", loggedIn = loggedIn, username = username, session = session, perms = perms)

def clear():
  for i in db.keys():
    del db[i]

@app.route("/login")
def login():
  loggedIn = request.cookies.get("loggedIn")
  username = request.cookies.get("username")
  session = request.cookies.get("session")
  perms = 'none'
  if loggedIn == "true":
    if username != None and username in db.keys():
      if ph.verify(session, username) == True:
        perms = db[username+"stat"]
  if loggedIn == "true":
    return redirect("/")
  else:
    return render_template("login.html", loggedIn = loggedIn, username = username, session = session, perms = perms)

@app.route("/signup")
def signup():
  loggedIn = request.cookies.get("loggedIn")
  username = request.cookies.get("username")
  session = request.cookies.get("session")
  perms = 'none'
  if loggedIn == "true":
    if username != None and username in db.keys():
      if ph.verify(session, username) == True:
        perms = db[username+"stat"]
  if loggedIn == "true":
    return redirect("/")
  else:
    return render_template("signup.html", loggedIn = loggedIn, username = username, session = session, perms = perms)

@app.route("/loginsubmit", methods=["GET", "POST"])
def loginsubmit():
  if request.method == "POST":
    username = request.form.get("username")
    password = request.form.get("password")
    if username in db.keys():
      if sha256_crypt.verify(password, db[username]) == True:
        resp = make_response(render_template('readcookie.html'))
        resp.set_cookie("loggedIn", "true")
        resp.set_cookie("username", username)
        resp.set_cookie("session", ph.hash(username))
        return resp
      else:
        return render_template("error.html", error="Incorrect Password, please try again.")
    else:
      return render_template("error.html", error="Account does not exist, please sign up.")

@app.route("/createaccount", methods=["GET", "POST"])
def createaccount():
  if request.method == "POST":
    newusername = request.form.get("newusername")
    newpassword = sha256_crypt.encrypt((request.form.get("newpassword")))
    orignewpass = request.form.get("newpassword")
    reenterpassword = request.form.get("reenterpassword")
    letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
    cap_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
    numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    allchars = letters + cap_letters + numbers + ['_']
    print(newusername)
    for i in newusername:
      if i not in allchars:
        return "Username can only contain alphanumeric characters and underscores."
    if newusername in db.keys():
      return render_template("error.html", error="Username taken.")
    if newusername == "":
      return render_template("error.html", error="Please enter a username.")
    if newpassword == "":
      return render_template("error.html", error="Please enter a password.")
    if reenterpassword == orignewpass:
      db[newusername] = newpassword
      db[newusername+"stat"] = "user"
      resp = make_response(render_template('readcookie.html'))
      resp.set_cookie("loggedIn", "true")
      resp.set_cookie("username", newusername)
      resp.set_cookie("session", ph.hash(newusername))
      return resp
    else:
      return render_template("error.html", error="Passwords don't match.")

@app.route("/logout")
def logout():
  resp = make_response(render_template('readcookie.html'))
  resp.set_cookie("loggedIn", "false")
  resp.set_cookie("username", "None")
  return resp

if __name__ == "__main__":
  app.run(debug=True, port=5000, host='0.0.0.0')
