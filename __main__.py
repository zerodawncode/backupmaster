from http import HTTPStatus
import requests
import json
import os
import logging
from confluent_kafka import Producer, KafkaError
import base64
import tempfile
import ssl
from prettytable import PrettyTable



# Your Mailgun API key and domain
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN", "")
MAILGUN_DEST_EMAIL = os.getenv("MAILGUN_DEST_EMAIL", "")
MAILGUN_URL = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"


# Appplatform envs
# KAFKA_BROKER=${db-kafka-syd1-71599.HOSTNAME}:${db-kafka-syd1-71599.PORT}
# KAFKA_USERNAME=${db-kafka-syd1-71599.USERNAME}
# KAFKA_PASSWORD=${db-kafka-syd1-71599.PASSWORD}
# KAFKA_CA_CERT=${db-kafka-syd1-71599.CA_CERT}



# Load Kafka configuration from environment variables
# KAFKA_BROKER = os.getenv("KAFKA_BROKER", "")
# KAFKA_USERNAME = os.getenv("KAFKA_USERNAME", "")
# KAFKA_PASSWORD = os.getenv("KAFKA_PASSWORD", "")

# KAFKA_CA_CERT = os.getenv("KAFKA_CA_CERT")
# KAFKA_CERT = os.getenv("KAFKA_CERT")
# KAFKA_KEY = os.getenv("KAFKA_KEY")

logging.basicConfig(level=logging.DEBUG)
logging.info("This is a log message")

# def decode_to_tempfile(ca_content):
#     tmp_file = tempfile.NamedTemporaryFile(delete=False)
#     tmp_file.write(ca_content.encode())
#     tmp_file.close()
#     return tmp_file.name


# def ssl_content(ca_content, directory='./', filename="ca_certificate.pem"):
#     # Replace escaped newlines and backslashes
#     ca_content = ca_content.replace("\\n", "\n").replace("\\", "").strip()
#
#     # Ensure the directory exists
#     if not os.path.exists(directory):
#         os.makedirs(directory)
#
#     # Save the certificate content to a file
#     file_path = os.path.join(directory, filename)
#     with open(file_path, 'w') as f:
#         f.write(ca_content)
#
#     # Load the SSL context with the content
#     ssl_context = ssl.create_default_context()
#     ssl_context.load_verify_locations(cadata=ca_content)
#
#     # Return the SSL context and the file path
#     return file_path
#
#
# # Create Kafka producer configuration
# def create_kafka_producer():
#     conf = {
#         'bootstrap.servers': KAFKA_BROKER,
#         'security.protocol': 'SASL_SSL',
#         'sasl.mechanism': 'SCRAM-SHA-512',
#         'ssl.ca.location': ssl_content(KAFKA_CA_CERT),
#         # 'ssl.certificate.location': decode_to_tempfile(KAFKA_CERT),
#         # 'ssl.key.location': decode_to_tempfile(KAFKA_KEY),
#         'sasl.username': KAFKA_USERNAME,
#         'sasl.password': KAFKA_PASSWORD,
#         'acks': 'all'
#     }
#     return Producer(conf)
#
#
# def send_to_kafka(referer, event, headers=None, result=None):
#     """
#     Send the validated data to Kafka.
#
#     :param result:
#     :param referer: The referer domain to create the topic name.
#     :param event: The event data to send to Kafka.
#     :param headers: The extracted headers to include in the Kafka message.
#     :return: True if message is delivered successfully, False otherwise.
#     """
#     if headers is None:
#         headers = {}
#     if result is None:
#         headers = {}
#     try:
#         producer = create_kafka_producer()
#         topic = referer.lower()  # Use referer as the Kafka topic name
#         message = {
#             "event": event,
#             "headers": headers,
#             "result": result
#         }
#
#         delivery_status = {"success": False}
#
#         def delivery_report(err, msg):
#             if err is not None:
#                 logging.error(f"Message delivery failed: {err}")
#             else:
#                 logging.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")
#                 delivery_status["success"] = True
#
#         producer.produce(topic, json.dumps(message), callback=delivery_report)
#         producer.flush()  # Ensure delivery
#
#         return delivery_status["success"]
#
#     except Exception as e:
#         logging.error(f"Kafka send error: {e}")
#         return False

# Function to flatten JSON recursively
def flatten_json(data, parent_key=""):
    flattened = {}
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            flattened.update(flatten_json(value, new_key))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            new_key = f"{parent_key}[{index}]"
            flattened.update(flatten_json(value, new_key))
    else:
        flattened[parent_key] = data
    return flattened

# Function to send email
def send_email(to_email, subject, body):
    response = requests.post(
        MAILGUN_URL,
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"Erparmour Postmaster <postmaster@{MAILGUN_DOMAIN}>",
            "to": to_email,
            "subject": subject,
            # "text": body,  # Sending as plain text
            "html": body,
        }
    )
    return response.status_code


def json_to_html_table(data):
    flattened_data = flatten_json(data)
    html = """<html>
    <head>
        <style>
            table { width: 100%%; border-collapse: collapse; font-family: Arial, sans-serif; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f4f4f4; }
        </style>
    </head>
    <body>
        <h2>RAW Data:</h2>
        <table>
            <tr><th>Key</th><th>Value</th></tr>"""

    for key, value in flattened_data.items():
        html += f"<tr><td>{key}</td><td>{value}</td></tr>"

    html += "</table></body></html>"
    return html

# Function to convert JSON to table
def json_to_table(data):
    flattened_data = flatten_json(data)
    table = PrettyTable(["Key", "Value"])
    for key, value in flattened_data.items():
        table.add_row([key, value])
    return table.get_string()


def load_recaptcha_keys(prefix="RECAPTCHA_KEY_"):
    """
    Dynamically loads all reCAPTCHA keys from environment variables with a given prefix.
    Example: RECAPTCHA_KEY_site1, RECAPTCHA_KEY_site2, ...

    :param prefix: The prefix for environment variables.
    :return: Dictionary mapping site names to secret keys.
    """
    recaptcha_keys = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            site_name = key[len(prefix):].lower()  # Store keys in lowercase for case-insensitive matching
            recaptcha_keys[site_name] = value
    return recaptcha_keys


def validate_recaptcha3(token, referer):
    """
    Validate reCAPTCHA v3 using a dynamically selected secret key.

    :param token: The response token from the frontend.
    :param referer: The referer domain to match against environment variables.
    :return: Dictionary with verification results.
    """
    recaptcha_keys = load_recaptcha_keys()
    site_key_name = referer.lower() if referer else None  # Normalize referer key

    secret_key = recaptcha_keys.get(site_key_name)

    if not secret_key:
        return {"error": "Invalid site key."}
    if not token:
        return {"error": "Missing reCAPTCHA token."}

    url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {"secret": secret_key, "response": token}

    try:
        response = requests.post(url, data=payload)
        result = response.json()
        logging.debug(result)
        return {
            "success": result.get("success", False),
            "score": result.get("score", 0),
            "action": result.get("action", ""),
            "hostname": result.get("hostname", ""),
            "error_codes": result.get("error-codes", [])
        }
    except requests.exceptions.RequestException as e:
        logging.error(f"reCAPTCHA validation error: {e}")
        return {"error": "Failed to validate reCAPTCHA."}


def make_response(body, status_code=HTTPStatus.OK):
    return {
        "statusCode": status_code,
        "body": body,
    }


def extract_headers(event):
    # Extract specific headers and values from the event data
    extracted_data = {
        "cf-ray": event.get("__ow_headers", {}).get("cf-ray"),
        "do-connecting-ip": event.get("__ow_headers", {}).get("do-connecting-ip"),
        "cf-ipcountry": event.get("__ow_headers", {}).get("cf-ipcountry"),
        "method": event.get("__ow_method"),
        "user-agent": event.get("__ow_headers", {}).get("user-agent"),
        "x-request-id": event.get("__ow_headers", {}).get("x-request-id")
    }

    # Return the extracted data
    return extracted_data


def main(event, context):
    """
    Main handler for validating reCAPTCHA based on referer and token.

    :param event: Incoming event payload.
    :param context: Execution context.
    :return: JSON response.
    """
    # return make_response({"message":extract_headers(event)},status_code=HTTPStatus.OK)
    try:
        token = event.get("recaptcha_token", False)
        ref = event.get("routemaster_ref", False) or event.get("ref", False) or event.get("referer", False)

        if not token:
            return make_response({"error": "Token is required."}, status_code=HTTPStatus.BAD_REQUEST)

        if not ref:
            return make_response({"error": "Reference is required."}, status_code=HTTPStatus.BAD_REQUEST)

        result = validate_recaptcha3(token, ref)

        if "error" in result:
            return make_response({"error": result["error"]}, status_code=HTTPStatus.BAD_REQUEST)

        if result.get("success", False) and result.get("score", 0) >= 0.1:
            # success = send_to_kafka(ref, event, extract_headers(event), result)
            table_str = json_to_html_table(event)
            success=send_email(MAILGUN_DEST_EMAIL, "New lead", table_str)
            if success==200 or success=='200':
                return make_response(
                    {'message': 'Validation is successful and data sent to be processed.', 'status': 'success'},
                    status_code=HTTPStatus.OK)

        return make_response({"error": "reCAPTCHA failed, Please reload the page."},
                             status_code=HTTPStatus.BAD_REQUEST)

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return make_response({"error": f"An internal error occurred."}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
