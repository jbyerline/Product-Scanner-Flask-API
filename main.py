from flask import Flask, jsonify, request, make_response, url_for, redirect
from flask_cors import CORS
import urllib.request
import re
import requests
import urllib.parse
import urllib.error
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

driver = None
# filePath = "/home/jbyerline/ProductScanner/products.json"
filePath = "products.json"


def scan_for_products(products_to_scan):
    # For each product
    for product in products_to_scan['products']:
        # If it is enabled
        if product['isEnabled']:
            # Load the URL:
            driver.get(product['scanURL'])
            # Grab the source code
            response = driver.page_source
            # Strip any weird JSON
            html = str(response).replace('\\', '')
            # print(html)
            # increment the number of trials
            product['numberOfTrials'] = product['numberOfTrials'] + 1
            if product['negateRegex']:
                # If the regex does not find a match
                if not re.search(product['regex'], html):
                    for num in product["contactNumbers"]:
                        # Sent Texts
                        headers = {"charset": "utf-8", "Content-Type": "application/json"}
                        url = 'https://text.byerline.me/send'
                        text_body = {
                            "phoneNumber": num,
                            "message": "Product Scanner: " + product["name"] + " is in stock. Access it here: \n\n" +
                                       product["productURL"],
                        }
                        requests.post(url, json=text_body, headers=headers)
                    # Update product values in JSON file
                    product['isFound'] = True
                    product['isEnabled'] = False
                    product['lastFound'] = datetime.now().strftime("%m-%d-%Y %I:%M:%S %p")
                    products_to_scan['numberFound'] = products_to_scan['numberFound'] + 1
                else:
                    product['isFound'] = False
            else:
                # If the regex does find a match
                if re.search(product['regex'], html):
                    for num in product["contactNumbers"]:
                        # Sent Texts
                        headers = {"charset": "utf-8", "Content-Type": "application/json"}
                        url = 'https://text.byerline.me/send'
                        text_body = {
                            "phoneNumber": num,
                            "message": "Product Scanner: " + product["name"] + " is in stock. Access it here: \n\n" +
                                       product["productURL"],
                        }
                        requests.post(url, json=text_body, headers=headers)
                    # Update product values in JSON file
                    product['isFound'] = True
                    product['isEnabled'] = False
                    product['lastFound'] = datetime.now().strftime("%m-%d-%Y %I:%M:%S %p")
                    products_to_scan['numberFound'] = products_to_scan['numberFound'] + 1
                else:
                    product['isFound'] = False
    # Update timestamp
    products_to_scan['lastUpdated'] = datetime.now().strftime("%m-%d-%Y %I:%M:%S %p")
    # Once all products have been checked, overwrite file.
    f = open(filePath, "w")
    f.write(json.dumps(products_to_scan, indent=4))
    f.close()


@app.before_first_request
def init_app():
    requests.get(
        'https://text.byerline.me/send/6193419322/' + urllib.parse.quote("Product Scanner has started."))
    # Configure and Start Google Chrome
    global driver
    options = Options()
    options.headless = True
    options.add_argument('--no-proxy-server')
    options.add_argument('--proxy-server="direct://"')
    options.add_argument('--proxy-bypass-list=*')
    options.add_argument('--window-size=1920,1200')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--blink-settings=imagesEnabled=false')
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X "
                                                                         "10_15_7) AppleWebKit/537.36 (KHTML, "
                                                                         "like Gecko) Chrome/98.0.4758.109 "
                                                                         "Safari/537.36", "platform": "Windows"})


@app.route('/scan')
def initiate_scan():
    # Read in product data
    f = open(filePath)
    products_to_scan = json.load(f)
    f.close()
    # Scan for updates
    scan_for_products(products_to_scan)
    # Read in updated product data
    f = open(filePath)
    updated_json = json.load(f)
    f.close()
    # Return contents of updated file
    return json.dumps(updated_json, indent=4)


@app.route('/data')
def get_data():
    # Read in product data
    f = open(filePath)
    products_to_scan = json.load(f)
    f.close()
    # Return contents of updated file
    return json.dumps(products_to_scan, indent=4)


@app.route('/update/<int:id>/<state>')
def update_product_state(id, state):
    # Read in product data
    f = open(filePath)
    products_to_scan = json.load(f)
    f.close()
    # Create local variable for boolean state
    bool_state = False
    # Manually cast String to Boolean
    if state == "True" or state == 'true':
        bool_state = True
    # Iterate over all of the products in the file
    for product in products_to_scan['products']:
        # Find the product with the ID to update
        if product['id'] == id:
            # Update product state
            product['isEnabled'] = bool_state
    # Overwrite file with new state
    f = open(filePath, "w")
    f.write(json.dumps(products_to_scan, indent=4))
    f.close()
    # Return contents of updated file
    return json.dumps(products_to_scan, indent=4)


@app.route('/loadPage', methods=['POST'])
def create_row_in_gs():
    if request.method == 'POST':
        try:
            driver.get(request.json['url'])
            page_content = driver.page_source
            print("regex: ", request.json['regex'], "\nnegateRegex: ", request.json['negateRegex'])
            if request.json['negateRegex']:
                if not re.search(request.json['regex'], page_content):
                    regex_response = "Regex Match Found"
                else:
                    regex_response = "Regex Match Not Found"
            if not request.json['negateRegex']:
                if re.search(request.json['regex'], page_content):
                    regex_response = "Regex Match Found"
                else:
                    regex_response = "Regex Match Not Found"

            response = {"url": request.json['url'], "regex": request.json['regex'],
                        "negateRegex": request.json['negateRegex'], "regexResponse": regex_response,
                        "pageContent": page_content}
            return response
        except KeyError:
            return "Key \"url\" or \"regex\" or \"negateRegex\" not provided", 400




if __name__ == '__main__':
    app.run(host="0.0.0.0")
