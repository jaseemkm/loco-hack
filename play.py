from base64 import b64encode
from os import makedirs
from os.path import join, basename
from sys import argv
import json
import requests
import os
from PIL import Image
import re

CLOUD_VISION_ENDPOINT_URL = 'https://vision.googleapis.com/v1/images:annotate'

from googleapiclient.discovery import build
import pprint

api_key = "YOUR_GOOGLE_API_KEY"
cse_id = "YOUR_CUSTOM_GOOGLE_SEARCH_ENGINE_ID"

def google_search(search_term, api_key, cse_id, **kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    res = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()
    return res['items']

def scores_with_options(question,options,**kwargs):
    service = build("customsearch", "v1", developerKey=api_key)
    scores = [0,0,0]
    for idx, option in enumerate(options):
        res = service.cse().list(q=question+' '+option, cx=cse_id, **kwargs).execute()
        scores[idx] = int(res['searchInformation']['totalResults'])
    return scores

def normal_scores(question,options):
    results = google_search(question, api_key, cse_id, num=10)
    scores = [0,0,0]
    for idx, result in enumerate(results):
        snippet = result['snippet']
        for n, option in enumerate(options):
            occurences = snippet.lower().count(option)
            scores[n] = occurences+scores[n]
    return scores

def make_image_data_list(image_filenames):
    """
    image_filenames is a list of filename strings
    Returns a list of dicts formatted as the Vision API
        needs them to be
    """
    img_requests = []
    for imgname in image_filenames:
        with open(imgname, 'rb') as f:
            ctxt = b64encode(f.read()).decode()
            img_requests.append({
                    'image': {'content': ctxt},
                    'features': [{
                        'type': 'TEXT_DETECTION',
                        'maxResults': 1
                    }]
            })
    return img_requests

def make_image_data(image_filenames):
    """Returns the image data lists as bytes"""
    imgdict = make_image_data_list(image_filenames)
    return json.dumps({"requests": imgdict }).encode()

def request_ocr(api_key, image_filenames):
    response = requests.post(CLOUD_VISION_ENDPOINT_URL,
                             data=make_image_data(image_filenames),
                             params={'key': api_key},
                             headers={'Content-Type': 'application/json'})
    return response

def get_text_from_response(response):
    t = response['textAnnotations'][0]
    return (t['description'])

def take_screenshot():
    os.system("adb exec-out screencap -p > screen.png")

def split_screen_to_question_and_options():
    i = Image.open('screen.png')
    width, height = i.size
    frame = i.crop(((0,400,width,650)))
    frame.save('question.png')
    frame = i.crop(((0,650,width,750)))
    frame.save('1.png')
    frame = i.crop(((0,750,width,850)))
    frame.save('2.png')
    frame = i.crop(((0,850,width,1000)))
    frame.save('3.png')


option_names = ['A','B','C']

def print_scores(scores,method):
    print (method+'\n-----------------------------')
    print ("Most relevant : "+ str(option_names[scores.index(max(scores))]))
    print ("Least relevant : "+ str(option_names[scores.index(min(scores))]))


if __name__ == '__main__':
    while True:
        a = raw_input("Wait for the next question and press Enter key instantly when it's displayed\n")
        take_screenshot()
        split_screen_to_question_and_options()
        image_filenames = ['question.png','1.png','2.png','3.png']
        response = request_ocr(api_key, image_filenames)
        if response.status_code != 200 or response.json().get('error'):
            print(response.text)
        else:
            responses = (response.json()['responses'])
            question = get_text_from_response(responses[0])
            question = re.sub('[^A-Za-z0-9\s]+', '', question)
            options = [get_text_from_response(responses[1]),get_text_from_response(responses[2]),get_text_from_response(responses[3])]
            for idx,option in enumerate(options):
                options[idx] = option.strip(' \t\n\r').lower()
            normal = normal_scores(question,options)
            print_scores(normal,'Method 1 (Question search)')
            withoption = scores_with_options(question,options)
            print_scores(withoption,'Method 2 (Question and options search)')