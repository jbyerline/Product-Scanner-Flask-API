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
filePath = "/home/jbyerline/ProductScanner/products.json"
# filePath = "products.json"


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
    # requests.get(
    #     'https://text.byerline.me/send/6193419322/' + urllib.parse.quote("Product Scanner has started."))
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


@app.route('/scan', methods=['GET'])
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


@app.route('/data', methods=['GET'])
def get_data():
    # Read in product data
    f = open(filePath)
    products_to_scan = json.load(f)
    f.close()
    # Return contents of updated file
    return json.dumps(products_to_scan, indent=4)


@app.route('/update/<int:id>/<state>', methods=['GET'])
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


@app.route('/remove/<int:id>', methods=['GET'])
def remove_product(id):
    # Read in product data
    f = open(filePath)
    products_list = json.load(f)
    f.close()

    index_to_remove = None

    # Iterate over all the products in the file
    for i in range(len(products_list['products'])):
        if products_list['products'][i]['id'] == id:
            index_to_remove = i

    if index_to_remove is None:
        return "ID: " + str(id) + " not found", 400

    products_list['products'][index_to_remove:index_to_remove + 1] = []

    # Overwrite file with new state
    f = open(filePath, "w")
    f.write(json.dumps(products_list, indent=4))
    f.close()

    return "Product with ID: " + str(id) + " removed.", 200


@app.route('/add', methods=['POST'])
def add_product():
    # Parse POST Body
    try:
        # Verify all the necessary fields are in the body
        brand = request.json['brand']
        name = request.json['name']
        image = request.json['image']
        product_url = request.json['productURL']
        scan_url = request.json['scanURL']
        regex = request.json['regex']
        negate_regex = request.json['negateRegex']
        contact_numbers = request.json['contactNumbers']

        # Read in current products
        f = open(filePath)
        product_list = json.load(f)
        f.close()
        print(product_list)

        # Find id for new product
        product_id = product_list["products"][len(product_list["products"])-1]["id"] + 1

        # Set other default fields
        is_found = False
        last_found = "N/A"
        number_of_trials = 0
        is_enabled = True

        # Form object
        new_product = {
            "id": product_id,
            "brand": brand,
            "name": name,
            "image": image,
            "productURL": product_url,
            "scanURL": scan_url,
            "regex": regex,
            "negateRegex": negate_regex,
            "isFound": is_found,
            "lastFound": last_found,
            "numberOfTrials": number_of_trials,
            "isEnabled": is_enabled,
            "contactNumbers": [contact_numbers]
        }

        # Add new product to array
        product_list["products"].append(new_product)

        # Overwrite file with new state
        f = open(filePath, "w")
        f.write(json.dumps(product_list, indent=4))
        f.close()

        return "Products Updated", 200

    except KeyError:
        return "Missing one or more keys. {\"brand\" \"name\" \"image\" \"productURL\" \"scanURL\" \"regex\" " \
               "\"negateRegex\" \"contactNumbers\"}", 400


@app.route('/addPhone', methods=['Patch'])
def add_phone():
    try:
        # Verify all the necessary fields are in the body
        id = request.json['id']
        contact_number = request.json['contactNumber']

        # Read in current products
        f = open(filePath)
        product_list = json.load(f)
        f.close()
        print(product_list)

        # Iterate over all of the products in the file
        for product in product_list['products']:
            # Find the product with the ID to update
            if product['id'] == id:
                # Check if phone number already exists
                if contact_number in product['contactNumbers']:
                    return "Number already exists", 400
                else:
                    product['contactNumbers'].append(contact_number)

        # Overwrite file with new state
        f = open(filePath, "w")
        f.write(json.dumps(product_list, indent=4))
        f.close()

        return "Products Updated", 200

    except KeyError:
        return "Missing one or more keys. {\"id\" \"contactNumber\"}", 400


@app.route('/removePhone', methods=['Patch'])
def remove_phone():
    try:
        # Verify all the necessary fields are in the body
        id = request.json['id']
        contact_number = request.json['contactNumber']

        # Read in current products
        f = open(filePath)
        product_list = json.load(f)
        f.close()
        print(product_list)

        product_index = None
        phone_index_to_remove = None

        # Iterate over all the products in the file
        for i in range(len(product_list['products'])):
            if product_list['products'][i]['id'] == id:
                product_index = i
                for j in range(len(product_list['products'][i]['contactNumbers'])):
                    if product_list['products'][i]['contactNumbers'][j] == contact_number:
                        phone_index_to_remove = j

        if product_index is None:
            return "ID: " + str(id) + " not found", 400
        elif phone_index_to_remove is None:
            return "Phone Number: " + str(contact_number) + " was not found", 400

        product_list['products'][product_index]["contactNumbers"][phone_index_to_remove:phone_index_to_remove + 1] = []

        # Overwrite file with new state
        f = open(filePath, "w")
        f.write(json.dumps(product_list, indent=4))
        f.close()

        return "Products Updated", 200

    except KeyError:
        return "Missing one or more keys. {\"id\" \"contactNumber\"}", 400


@app.route('/loadPage', methods=['POST'])
def load_page():
    try:
        url = request.json['url']
        negate_regex = request.json['negateRegex']
        regex = request.json['regex']
        regex_response = False

        driver.get(url)
        page_content = driver.page_source

        if negate_regex:
            if not re.search(regex, page_content):
                regex_response = True
            else:
                regex_response = False
        if not negate_regex:
            if re.search(regex, page_content):
                regex_response = True
            else:
                regex_response = False

        response = {"url": url, "regex": regex, "negateRegex": negate_regex, "regexMatchFound": regex_response, "pageContent": page_content}, 200

        return response

    except KeyError:
        return "Missing one or more keys. {[}\"url\" or \"regex\" or \"negateRegex\"}", 400


if __name__ == '__main__':
    app.run(host="0.0.0.0")
