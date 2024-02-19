import whisper
import datetime
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = whisper.load_model("base")


class Conversation:
    prompt = "You are a physiotherapist. You will now be connected to a patient (the user). You are to ask them about these following exercises one at a time to see how they are progressing. Please maintain a professional tone and keep your questions succint. Your goal is to quickly acquire all the required information from the patient. Use your professional knowledge to help inform your questions relative to each exercise. Here are the exercises:"

    def __init__(self, user_doc_ref, conversaton_id=None):
        if conversaton_id:
            self.conversation_ref = user_doc_ref.collection("conversations").document(
                conversaton_id
            )
            self.history = self.conversation_ref.get().get("history")
        else:
            self.history = []
            _, self.conversation_ref = user_doc_ref.collection("conversations").add(
                {"date": datetime.datetime.now(), "history": self.history}
            )
            self.engineer_prompt(user_doc_ref)

    def get_conversation_id(self):
        return self.conversation_ref.id

    @staticmethod
    def transcribe(audio_file):
        return model.transcribe(audio_file, fp16=False).get("text")

    def request_reply(self):
        return client.chat.completions.create(
            model="gpt-3.5-turbo", messages=self.history, temperature=0.5
        )

    def generate_reply(self, text):
        self.history.append({"role": "user", "content": text})
        self.conversation_ref.update({"history": self.history})
        response = self.request_reply()
        self.history.append(
            {
                "role": "assistant",
                "content": response.choices[0].message.content.strip(),
            }
        )
        self.conversation_ref.update({"history": self.history})
        return response.choices[0].message.content.strip()

    def engineer_prompt(self, user_doc_ref):
        exercises = user_doc_ref.get().get("exercises")
        if exercises:
            for exercise in exercises:
                self.prompt += "\n" + exercise

        self.prompt += f". When necessary, please refer the patient to contact their physiotherapist who's name is: {user_doc_ref.parent.parent.get().get('name')}."

    def end_conversation(self):
        # Summarize the entire conversation
        self.history.append(
            {
                "role": "system",
                "content": """Summarize the entire conversation between the user 
                    and the assistant. Focus on the answers the user gave, in context of how
                    they are physically feeling and progressing with their exercises.
                    The summary wil be used to quickly inform the physiotherapist of 
                    important information they should be aware of about the patient.
                    Return only the summary, no other text.""",
            }
        )
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", messages=self.history, temperature=0.5
        )
        self.summary = response.choices[0].message.content.strip()

        # Determine if the summary is relevant to the physio
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": self.summary,
                },
                {
                    "role": "system",
                    "content": """Does the summary above contain information about 
                    a patient that is relevant to a physiotherapist's job? Key 
                    topics would include their health, progress on their assigned
                    exercises, and physical issues they have experienced.
                    
                    Return only a T or F, indicating if the summary is classified as relevant. 
                    """,
                },
            ],
            temperature=0.5,
        )

        # Store relevant summary or delete conversation
        if response.choices[0].message.content.strip() == "T":
            self.conversation_ref.update({"summary": self.summary})
            return self.summary
        else:
            self.conversation_ref.delete()
            return ""
