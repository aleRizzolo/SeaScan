import os
import json
import boto3
import telebot
import subprocess
from telebot import types
from dotenv import dotenv_values, load_dotenv
from botocore.exceptions import NoCredentialsError
from telebot.types import ReplyKeyboardMarkup, KeyboardButton


# Load variables from .env file
env_vars = dotenv_values(".env")

# Extra commands
# /clean - clear all table
# /test - call lambda activeMonitoring
# /end - delete all tables

load_dotenv()

TOKEN = env_vars["BOT_TOKEN"]
CHAT_ID = env_vars["CHAT_ID"]
url = "http://localhost:4566"

bot = telebot.TeleBot(TOKEN)
dynamoDb = boto3.resource("dynamodb", endpoint_url=url)

print("⚡ Bot started")


def query_data_dynamodb(table):
    measurementTable = dynamoDb.Table(table)
    response = measurementTable.scan()
    return response["Items"]


def format_message(result):
    formatted_message = ""
    for item in result:
        beach = item["beach"]
        ph = item["ph"]
        hydrocarbons = item["hydrocarbons"]
        # Extracting only the date portion
        daytime = item["dayTime"].split(",")[0]

        formatted_message += (
            f"- {beach}: ph: {ph}, hydrocarbons: {hydrocarbons}, daytime: {daytime}\n"
        )

    return formatted_message


def retrievePHAverage(result):
    formatted_message = ""
    for item in result:
        beach = item["beach"]
        ph = item["ph"]
        # Extracting only the date portion
        daytime = item["dayTime"].split(",")[0]

        formatted_message += f"- {beach}: ph: {ph}, daytime: {daytime}\n"

    return formatted_message


def retrieveHydroAverage(result):
    formatted_message = ""
    for item in result:
        beach = item["beach"]
        hydrocarbons = item["hydrocarbons"]
        # Extracting only the date portion
        daytime = item["dayTime"].split(",")[0]

        formatted_message += f"- {beach}: hydrocarbons: {hydrocarbons}, daytime: {daytime}\n"

    return formatted_message


@bot.message_handler(commands=["start"])
def first_start(message):
    cid = message.chat.id
    bot.send_message(
        cid,
        f"Welcome {message.from_user.username}, press /help to get the list of commands",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["help"])
def send_help(message):
    cid = message.chat.id

    # Create the inline buttons
    button_generate_data = types.InlineKeyboardButton(
        "Generate Data", callback_data="generateData"
    )
    button_average_ph = types.InlineKeyboardButton(
        "Average PH", callback_data="averagePH"
    )
    button_average_hydrocarbons = types.InlineKeyboardButton(
        "Average Hydrocarbons", callback_data="averageHydrocarbons"
    )
    button_send_email = types.InlineKeyboardButton(
        "Send Email", callback_data="sendEmail"
    )
    button_switch_sensor_on = types.InlineKeyboardButton(
        "Switch Sensor On", callback_data="switchSensorOn"
    )
    button_switch_sensor_off = types.InlineKeyboardButton(
        "Switch Sensor Off", callback_data="switchSensorOff"
    )
    button_activate_sensors = types.InlineKeyboardButton(
        "Activate Sensors", callback_data="ONsensors"
    )
    button_deactivate_sensors = types.InlineKeyboardButton(
        "Deactivate Sensors", callback_data="OFFsensors"
    )

    # Create the inline keyboard markup
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        button_generate_data,
        button_average_ph,
        button_average_hydrocarbons,
        button_send_email,
        button_switch_sensor_on,
        button_switch_sensor_off,
        button_activate_sensors,
        button_deactivate_sensors,
    )

    # Send the message with inline buttons
    bot.send_message(cid, "Choose a command:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def handle_button_click(call):
    if call.data == "generateData":
        generate_data(call.message)
    elif call.data == "averagePH":
        averagePH(call.message)
    elif call.data == "averageHydrocarbons":
        averageHydrocarbons(call.message)
    elif call.data == "sendEmail":
        sendEmail(call.message)
    elif call.data == "switchSensorOn":
        switchSensorOn(call.message)
    elif call.data == "switchSensorOff":
        switchSensorOff(call.message)
    elif call.data == "ONsensors":
        ONsensors(call.message)
    elif call.data == "OFFsensors":
        OFFsensors(call.message)


@bot.message_handler(commands=["generateData"])
# Execute the TypeScript file
def generate_data(message):
    cid = message.chat.id
    # command = ["node", f"{os.getcwd()}\\dist\\device.js"]
    command = ["node", "..\\dist\\device.js"]
    try:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output, error = process.communicate()
    except Exception as e:
        print(e)
    output = output.decode("utf-8")
    error = error.decode("utf-8")
    if process.returncode != 0:
        print(f"Error executing Node.js script: {error}")
        bot.send_message(cid, "error generating data")
    else:
        print(f"Output:\n{output}")
        bot.send_message(cid, "Processing....")
        lambda_client = boto3.client("lambda", endpoint_url=url)
        response = lambda_client.invoke(
            FunctionName="average",
            InvocationType="RequestResponse",
            Payload=json.dumps({"cid": cid}),
        )
        bot.send_message(cid, "Done!")


@bot.message_handler(commands=["averagePH"])
def averagePH(message):
    cid = message.chat.id
    try:
        result = query_data_dynamodb("SeaScan")
    except Exception as e:
        print(e)
    bot.send_message(cid, retrievePHAverage(result))


@bot.message_handler(commands=["averageHydrocarbons"])
def averageHydrocarbons(message):
    cid = message.chat.id
    try:
        result = query_data_dynamodb("SeaScan")
    except Exception as e:
        print(e)
    bot.send_message(cid, retrieveHydroAverage(result))


@bot.message_handler(commands=["sendEmail"])
def sendEmail(message):
    cid = message.chat.id
    try:
        bot.send_message(cid, "Please insert your email")
        bot.register_next_step_handler(message, process_email)
    except Exception as e:
        bot.send_message(cid, f"Error sending email: {str(e)}")


def process_email(message):
    cid = message.chat.id
    recipient = message.text

    try:
        subject = f"Email from {bot.get_me().username}"
        body = format_message(query_data_dynamodb("SeaScan"))
        sender = env_vars["SENDER_EMAIL"]

        send_email(subject, body, sender, recipient)
        bot.send_message(cid, "Email sent successfully!")
    except Exception as e:
        bot.send_message(cid, f"Error sending email: {str(e)}")


def send_email(subject, body, sender, recipient):
    aws_access_key_id = env_vars["AWS_ACCESS_KEY_ID"]
    aws_secret_access_key = env_vars["AWS_SECRET_ACCESS_KEY"]
    aws_region = env_vars["REGION"]

    # Configure Boto3 client for SES
    ses_client = boto3.client(
        "ses",
        region_name=aws_region,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=env_vars["ENDPOINT"],
    )

    try:
        response = ses_client.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient]},
            Message={"Subject": {"Data": subject},
                     "Body": {"Text": {"Data": body}}},
        )
        print("Email sent! Message ID:", response["MessageId"])
    except NoCredentialsError:
        print("Failed to send email: AWS credentials not found.")


@bot.message_handler(commands=["OFFsensors"])
def OFFsensors(message):
    cid = message.chat.id

    try:
        lambda_client = boto3.client("lambda", endpoint_url=url)
        response = lambda_client.invoke(
            FunctionName="offsensors",
            InvocationType="RequestResponse",
            Payload=json.dumps({"cid": cid}),
        )

        bot.send_message(cid, "Active status updated successfully!")

    except Exception as e:
        bot.send_message(cid, f"Error updating active status: {str(e)}")


@bot.message_handler(commands=["ONsensors"])
def ONsensors(message):
    cid = message.chat.id

    try:
        lambda_client = boto3.client("lambda", endpoint_url=url)
        response = lambda_client.invoke(
            FunctionName="onsensors",
            InvocationType="RequestResponse",
            Payload=json.dumps({"cid": cid}),
        )

        bot.send_message(cid, "Active status updated successfully!")

    except Exception as e:
        bot.send_message(cid, f"Error updating active status: {str(e)}")


@bot.message_handler(commands=["switchSensorOn"])
def switchSensorOn(message):
    cid = message.chat.id

    try:
        table = dynamoDb.Table("SeaScan")
        response = table.scan()
        items = response["Items"]

        # Extract the unique beach from the items
        beach = list(set(item["beach"] for item in items))

        if not beach:
            bot.send_message(cid, "No beach found in the table.")
            return

        # Create the reply keyboard markup with buttons for each beach
        keyboard = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
        buttons = [KeyboardButton(beach) for beach in beach]
        keyboard.add(*buttons)

        # Send the beach selection prompt with buttons
        bot.send_message(cid, "Select a beach:", reply_markup=keyboard)

        # Register the next step handler to capture the selected beach
        bot.register_next_step_handler(message, process_beach_selection_on)

    except Exception as e:
        bot.send_message(cid, f"Error toggling active status: {str(e)}")


@bot.message_handler(commands=["switchSensorOff"])
def switchSensorOff(message):
    cid = message.chat.id

    try:
        table = dynamoDb.Table("SeaScan")
        response = table.scan()
        items = response["Items"]

        # Extract the unique beach from the items
        beach = list(set(item["beach"] for item in items))

        if not beach:
            bot.send_message(cid, "No beach found in the table.")
            return

        # Create the reply keyboard markup with buttons for each beach
        keyboard = ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
        buttons = [KeyboardButton(beach) for beach in beach]
        keyboard.add(*buttons)

        # Send the beach selection prompt with buttons
        bot.send_message(cid, "Select a beach:", reply_markup=keyboard)

        # Register the next step handler to capture the selected beach
        bot.register_next_step_handler(message, process_beach_selection_off)

    except Exception as e:
        bot.send_message(cid, f"Error toggling active status: {str(e)}")


def process_beach_selection_on(message):
    cid = message.chat.id
    beach = message.text

    lambda_client = boto3.client("lambda", endpoint_url=url)
    response = lambda_client.invoke(
        FunctionName="onsensorbeach",
        InvocationType="RequestResponse",
        Payload=json.dumps({"table": "SeaScan", "beach": beach}),
    )
    bot.send_message(cid, "Done")


def process_beach_selection_off(message):
    cid = message.chat.id
    beach = message.text

    lambda_client = boto3.client("lambda", endpoint_url=url)
    response = lambda_client.invoke(
        FunctionName="offsensorbeach",
        InvocationType="RequestResponse",
        Payload=json.dumps({"table": "SeaScan", "beach": beach}),
    )
    bot.send_message(cid, "Done")


bot.polling()
