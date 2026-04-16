import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
import time
import requests
import json
from datetime import datetime, timezone, timedelta

API_URL = "https://graduationproject-production-e0b1.up.railway.app/api/chat/withMessages/all"

load_dotenv()

client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
    )

def fetch_conversations(user_token):
    JWT_TOKEN = user_token
    headers = {
        "Authorization": f"Bearer {JWT_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.get(API_URL, headers=headers)

    if response.status_code == 200:
        data = response.json()
        # data = response
        print("Fetch Conversations Succeed")
        return data
    else:
        # print("Error:", response.status_code)
        print(f'''Error: {response.status_code}\n{response.text}''')
        return f'''Error: {response.status_code}\n{response.text}'''

def format_previous_messages(conv, start_of_week, end_of_week):
    messages = sorted(conv["messages"], key=lambda m: m["createdAt"])
    context_msgs = []
    weekly_msgs = []

    for msg in messages:
        msg_time = datetime.fromisoformat(
            msg["createdAt"].replace("Z", "+00:00")
        )

        if msg_time < start_of_week:
            context_msgs.append(msg)
        elif start_of_week <= msg_time < end_of_week:
            weekly_msgs.append(msg)

    context_msgs = context_msgs[-4:]
    conv["messages"] = context_msgs + weekly_msgs
    return conv

def filter_this_week(data):
    now = datetime.now(timezone.utc)

    conversations_data = data["conversations"]

    days_since_saturday = (now.weekday() + 2) % 7
    start_of_week = now - timedelta(days=days_since_saturday)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)
    # print(start_of_week, end_of_week)

    filtered = []
    for conv in conversations_data:
        created_at = datetime.fromisoformat(
            conv["conversation"]["createdAt"].replace("Z", "+00:00")
        )
        last_message_at = datetime.fromisoformat(
            conv["conversation"]["lastMessageAt"].replace("Z", "+00:00")
        )

        if (start_of_week <= created_at < end_of_week or
            start_of_week <= last_message_at < end_of_week):
            if created_at < start_of_week:
                format_previous_messages(conv, start_of_week, end_of_week)
            filtered.append(conv)

    data["conversations"] = filtered
    return data

def format_conversations(history):
    conversations = sorted(history["conversations"], key=lambda c: c["conversation"]["createdAt"])
    formatted_conversations = ""
    for i, conversation in enumerate(conversations):

        messages = sorted(conversation["messages"], key=lambda m: m["createdAt"])

        formatted_conversations+=f"Conversation {i+1}:\n"
        for msg in messages:
            if msg["sender"] == "user":
                formatted_conversations += f"User: {msg['message']}\n"
        formatted_conversations += "\n"
    # print(formatted_conversations)
    return formatted_conversations

def generate_report(conversations):
    # model = "models/gemini-2.5-flash"
    model = "models/gemini-3.1-flash-lite-preview"

    prompt = f"""
    Analyze the following weekly conversations:

    {conversations}
    """

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text="""
You are a supportive AI mental health assistant (not a licensed therapist).

Your role is to analyze user conversations and provide helpful emotional insights and supportive feedback directly to the user in the form of a weekly report.

Follow these rules strictly:

- Be empathetic, kind, and non-judgmental.
- Do NOT diagnose any mental illness.
- Do NOT provide medical or clinical advice.
- Focus on identifying emotions, patterns, and overall well-being across the entire week.
- Use warm, supportive, and human-like language.
- Speak directly to the user using "you".
- Do NOT refer to "the user" — make it personal and conversational.
- Keep the response clear, structured, and easy to understand.

- This is a weekly summary, not a real-time analysis:
  - Do NOT describe the user’s current or immediate feelings (e.g., avoid "you are feeling now").
  - Do NOT refer to specific days or moments directly.
  - Focus on overall emotional trends across the conversations.
  - Describe patterns over time using varied and natural expressions (do not repeat the same phrase).

- Use varied and natural phrasing when describing weekly patterns.
- Do NOT rely on a single repeated phrase (e.g., avoid always saying "over the past week").
- You may use different expressions such as:
  - "Throughout the week"
  - "Across recent conversations"
  - "There seems to be a pattern of"
  - "Overall"
  - "It looks like"
  - "In general"
- Avoid repetitive sentence structures across sections.

- Consider emotional changes across time (e.g., improvement, decline, or fluctuations).
- Do not base your analysis on a single message; analyze the overall pattern across the conversations.
- Pay attention to both repeated patterns and the general emotional trajectory.

If the conversation shows signs of significant emotional distress:
- Gently encourage the user to seek support from a trusted person or a mental health professional.
- Do this naturally within the feedback, not as a warning or alarm.
- Do NOT sound scary, alarming, or overly dramatic.

Always generate the response in the following format:

1. Emotional Summary
- Briefly describe the main emotions present over the week.

2. Key Patterns
- Highlight repeated thoughts, concerns, or behaviors across the conversations.

3. Supportive Feedback
- Provide empathetic, encouraging, and personal feedback addressed directly to the user.
- Keep the tone reflective of a weekly overview, not a momentary state.

4. Suggestions
- Offer simple, practical coping strategies (e.g., journaling, rest, talking to someone, organizing tasks).

- Tailor suggestions based on the user's overall emotional pattern:
  - If the user shows low energy → suggest gentle, low-effort activities.
  - If the user shows stress or overwhelm → suggest calming techniques.
  - If the user shows negative thinking → suggest reflective activities.

- You may also suggest helpful activities, or recommend a book, podcast, or video.

- When recommending books:
  - Suggest real, well-known books when possible.
  - Only provide a book title if you are confident it exists.
  - Do NOT invent or hallucinate book names.
  - Prefer simple, accessible, and widely known books.
  - Optionally include a short reason why the book may help.

- When recommending podcasts:
  - Suggest real, well-known podcasts when possible.
  - Only provide a podcast name if you are confident it exists.
  - Do NOT invent podcast names.
  - Prefer widely known or general mental health / self-improvement podcasts.
  - Optionally include a short reason why it may help.

- When recommending videos:
  - Suggest general types of videos (e.g., "a short video about breathing exercises").
  - Only mention specific creators or channels if you are confident they are real.
  - Do NOT invent video titles or creators.

- If unsure about any recommendation:
  - Fall back to suggesting a type of content instead of a specific name.

- Limit suggestions to 2–4 items maximum to avoid overwhelming the user.
- Make all suggestions feel natural, relevant, and supportive.

Return the response strictly in valid JSON format like:

{
  "emotional_summary": "",
  "patterns": [],
  "feedback": "",
  "suggestions": []
}
"""),
        ],
    )

    max_retries = 3
    for i in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )
            return response.text
        except Exception:
            print(f"Retry {i+1}...")
            time.sleep(2)
    return "Error: Unable to generate the report right now."

def Report(user_token):
    history=fetch_conversations(user_token)
    if isinstance(history, str) and history.startswith("Error"):
        return {"error": "invalid_token or expired token"}
    filter_this_week(history)
    conversations = format_conversations(history)
    report = generate_report(conversations)
    return report