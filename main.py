from flask import Flask, Response, request, jsonify, render_template, stream_with_context
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
from constants import *
import time
import firebase_admin
from firebase_admin import credentials
from flask_cors import CORS
from openai import OpenAI
import re

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")


def create_service_dict():
    variables_keys = {
        "type": os.getenv("TYPE"),
        "project_id": os.getenv("PROJECT_ID"),
        "private_key_id": os.getenv("PRIVATE_KEY_ID"),
        "private_key": os.getenv("PRIVATE_KEY"),
        "client_email": os.getenv("CLIENT_EMAIL"),
        "client_id": os.getenv("CLIENT_ID"),
        "auth_uri": os.getenv("AUTH_URI"),
        "token_uri": os.getenv("TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("CLIENT_X509_CERT_URL"),
        "universe_domain": os.getenv("UNIVERSE_DOMAIN"),
    }
    return variables_keys


cred = credentials.Certificate(create_service_dict())
firebase_admin.initialize_app(cred)

from conversation.views import conversation_blueprint
from exercise.views import exercise_blueprint

# Register the conversation Blueprint
app.register_blueprint(conversation_blueprint, url_prefix="/conversation")
app.register_blueprint(exercise_blueprint, url_prefix="/exercise")

CORS(app)

# Load Flask-Mail config from .env
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT"))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS").lower() == "true"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")
mail = Mail(app)


@app.route("/patient/send-link", methods=["POST"])
def send_link():
    try:
        data = request.get_json()
        practitionId = data.get("practitionId")
        patientId = data.get("patientId")
        name = data.get("name")
        email = data.get("email")

        # Send patient email with login link
        message = Message(
            subject=EMAIL_SUBJECT,
            recipients=[email],
            body=EMAIL_BODY_TEMPLATE.format(
                name=name, practitionId=practitionId, patientId=patientId
            ),
        )
        mail.send(message)

        return jsonify({"success": True, "message": "Email sent successfully"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def format_server_time():
    server_time = time.localtime()
    return time.strftime("%I:%M:%S %p", server_time)


@app.route("/")
def index():
    context = {"server_time": format_server_time()}
    return render_template("index.html", context=context)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/text_to_speech")
def texttospeech():
    def generate():
        input="Zelda II: The Adventure of Link[a] is an action role-playing video game with platforming elements developed and published by Nintendo. It is the second installment in the Legend of Zelda series and was released in Japan for the Famicom Disk System on January 14, 1987—less than one year after the Japanese release and seven months before the North American release of the original The Legend of Zelda. Zelda II was released in North America and the PAL region for the Nintendo Entertainment System in late 1988, almost two years after its initial release in Japan. The Adventure of Link is a direct sequel to the original The Legend of Zelda, again involving the protagonist Link, on a quest to save Princess Zelda, who has fallen under a sleeping spell. The game's emphasis on side-scrolling and role-playing elements is a significant departure from its predecessor. For much of the series' three-decade history, the game technically served as the only sequel to the original game, as all other entries in the series are either prequels or occur in an alternative reality, according to the official Zelda timeline. This changed with the release of Breath of the Wild in 2017 and Tears of the Kingdom in 2023, which serve as the latest chapters to the Zelda continuity.[3] The game was a critical and financial success and introduced elements such as Link's 'magic meter' and the Dark Link character that would become commonplace in future Zelda games, although the role-playing elements, such as experience points and limited lives have not been used since in canonical games. The Adventure of Link was followed by A Link to the Past for the Super Nintendo Entertainment System in 1991. Gameplay Zelda II: The Adventure of Link is an action role-playing game, bearing little resemblance to the first or later entries in the Legend of Zelda series. It features side-scrolling areas within a larger top-down world map, rather than the mostly top-down perspective of the previous game, which only uses side-scrolling in a few dungeon basement areas. The side-scrolling gameplay and experience system are similar to features of the Castlevania series, especially Castlevania II: Simon's Quest. The game incorporates a strategic combat system, a proximity continue system based on lives, an experience points system, magic spells, and more interaction with non-player characters. Apart from the non-canonical CD-i The Legend of Zelda games, Link: The Faces of Evil and Zelda: The Wand of Gamelon, no other game in the series includes a life feature. The side angle is occasionally seen in Link's Awakening and the other Game Boy entries, which rely primarily on the top-down view.[4] Experience levels In this installment, Link gains experience points to upgrade his attack, magic, and life by defeating enemies.[5] He can raise each of these attributes to a maximum of eight levels. Raising a life level will decrease the damage Link receives when hit, raising a magic level will decrease the magic points cost of spells, and raising an attack level will strengthen his sword's offensive power. In the Western version of the game, each attribute requires a different amount of experience to level up, with the life level requiring the fewest points to level and attack requiring the most. When enough points are acquired to raise an attribute, the player may choose to level up that attribute or to cancel and continue gaining experience points towards the next level in another attribute. In the original Japanese version, all attributes require the same number of experience points to level up, and the required number is lower, but if the player loses all of his lives, the levels of all attributes will be reset to the lowest of the three (while level upgrades in the Western version are permanent). Once Link has raised an attribute to the maximum level of eight, further advances in that attribute will e"
        sentences = re.split(r'(?<=[.!?])', input)
        # sentences = [sentence.strip() for sentence in sentences if sentence.strip()] Try leaving this out to allow for pauses in the text to speach
        for sentence in sentences:
            audio_response = client.audio.speech.create(
                model="tts-1",
                voice="shimmer",
                input=sentence,
                response_format="opus"
            )

            for audio_chunk in audio_response.iter_bytes(1024):
                yield audio_chunk
    return Response(stream_with_context(generate()), content_type='audio/opus')

if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=5000))