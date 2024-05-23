# -*- coding: utf-8 -*-

from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import time
from processing import *
import requests
import json
from scraper.scraper import *
import base64


app = Flask(__name__)
cors = CORS(app)

@app.route("/information")
def information():
    def stream():
        restaurants = []
        for i in range(4):
            restaurants.append([i, 'desc', "https://via.placeholder.com/150"]) 
        for i in range(4):
            msg = {"info": restaurants[i]}
            yield "data: " + json.dumps(msg) +  "\n\n"
            time.sleep(1)
        yield ":end\n\n"
    return Response(stream(), mimetype="text/event-stream")

@app.route("/get-foods", methods = ['POST'])
def getFoods():
    title = request.json["title"]
    reviews = request.json["reviews"]
    print(title, reviews)

    # reviews is an array of plain-text reviews
    food_nouns = findFoodNounsWithNER(reviews)
    sentences_per_food_nouns = mapSentencestoFoodNounsNER(food_nouns["food_nouns"], reviews, food_nouns["all_food_nouns_found"])
    food_score_results = getAverageSentimentScorePerWord(food_nouns["food_nouns"], sentences_per_food_nouns)
    results = getBestAndWorstFoods(food_score_results["food_score_result"], food_score_results["sentences_per_food_nouns"])

    return jsonify(result=results)

@app.route("/get-reviews", methods = ['POST'])
def getReviews():
    title = request.json["title"]
    url = request.json["url"]
    number_of_reviews = request.json["number_of_reviews"]
    print(title, url)

    data = scrape_for_reviews(False, number_of_reviews, url, 'newest')
    #response = requests.get(url)
    #data = json.dumps(response)
    return(jsonify(result=data))

@app.route("/get-restaurant", methods = ['POST'])
def getRestaurants():
    placeID = request.json["placeID"]["placeID"]
    print(placeID)

    # first get general call for the restaurant - REMEMBER to replace API key
    url = "https://maps.googleapis.com/maps/api/place/details/json?place_id=" + placeID + "&fields=name%2Crating%2Cformatted_address%2Cformatted_phone_number%2Cicon%2Cicon_background_color%2Copening_hours%2Cphotos&key=AIzaSyAIBn4vzxFYPHepZTaJc1_5wkhrK2sR9mQ"

    print(url)
    payload={}
    headers = {}

    response = requests.request("GET", url, headers=headers, data=payload)
    results = json.loads(response.text)["result"]

    data = {
        "rating": results["rating"],
        "formatted_address": results["formatted_address"],
        "formatted_phone_number" : "(02) 9374 4000",
        "icon" : results["icon"],
        "icon_background_color" : results["icon_background_color"],
        "name" : results["name"],
        "hours": results["opening_hours"]["weekday_text"],
        "open_now": results["opening_hours"]["open_now"]
    }

    photo_refs = results["photos"]
    photos = []
    for idx, ref in enumerate(photo_refs):
        new_url = "https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference=" + ref["photo_reference"] + "&key=AIzaSyAIBn4vzxFYPHepZTaJc1_5wkhrK2sR9mQ"
        payload={}
        headers = {}

        response = requests.request("GET", new_url, headers=headers, data=payload)

        if response.status_code == 200:
            image_data = response.content
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_json = {
                "image": image_base64,
                "filename": "image.jpg",  # Optional: Provide the filename
                "content_type": "image/jpeg"  # Optional: Provide the image content type
            }
            photos.append(image_json)
        else:
            print(response.status_code)
    data["photos"] = photos
    return(jsonify(result=data))
