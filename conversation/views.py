from flask import request, jsonify, Blueprint
from firebase_admin import firestore
from .conversation import (
    Conversation,
)
from firebase_admin import firestore
import tempfile
import os

conversation_blueprint = Blueprint("conversation", __name__)
db = firestore.client()
users_ref = db.collection("practitioners")

@conversation_blueprint.route("/start")
def start():
    practitioner = request.args.get("practitioner")
    patient = request.args.get("patient")
    user_doc_ref = (
        users_ref.document(practitioner).collection("patients").document(patient)
    )
    conversation = Conversation(user_doc_ref=user_doc_ref)
    return jsonify({"conversationID": conversation.get_conversation_id()}), 200

@conversation_blueprint.route("/send_message", methods=["POST"])
def send_message():
    conversation_id = request.args.get("id")
    practitioner = request.args.get("practitioner")
    patient = request.args.get("patient")
    user_doc_ref = (
        users_ref.document(practitioner).collection("patients").document(patient)
    )
    conversation = Conversation(
        user_doc_ref=user_doc_ref, conversaton_id=conversation_id
    )

    # Check if the request contains an audio or text message
    if "audioFile" in request.files:
        # Store audio in a temp file
        audio = request.files["audioFile"]
        temp_audio_path = os.path.join(tempfile.gettempdir(), "received_audio.wav")
        audio.save(temp_audio_path)
        # Transcribe the audio
        message = Conversation.transcribe(str(temp_audio_path))
        os.remove(temp_audio_path)
    else:
        message = request.json.get("message")

    # Generate a reply using the Conversation object
    reply = conversation.generate_reply(message)
    return jsonify({"reply": reply}), 200


@conversation_blueprint.route("/end")
def end():
    conversation_id = request.args.get("id")
    practitioner = request.args.get("practitioner")
    patient = request.args.get("patient")
    user_doc_ref = (
        users_ref.document(practitioner).collection("patients").document(patient)
    )
    # Retrieve the Conversation object based on the conversation ID
    conversation = Conversation(user_doc_ref, conversaton_id=conversation_id)
    summary = conversation.end_conversation()
    return jsonify({'reply': summary}), 200
