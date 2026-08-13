from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import json
import os
import requests

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)


# =========================
# CONFIG
# =========================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CHATS_FILE = DATA_DIR / "chat_store.json"
MEMORY_FILE = DATA_DIR / "memory_store.json"
BARBADOS_FILE = DATA_DIR / "barbados_knowledge.json"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# =========================
# APP
# =========================

app = FastAPI(title="BIM-CHAT API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# SCHEMAS
# =========================

class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    chat_id: str
    message: str
    model: str = DEFAULT_MODEL


class NewChatResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[Message]


class CurrencyRequest(BaseModel):
    amount: float
    from_currency: str
    to_currency: str = "BBD"


class WeatherRequest(BaseModel):
    latitude: float
    longitude: float


class MemoryRecord(BaseModel):
    key: str
    value: str


class ImageRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    quality: str = "standard"


# =========================
# FILE HELPERS
# =========================

def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def load_json(path: Path, default: Any):
    if not path.exists():
        save_json(path, default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        save_json(path, default)
        return default


def save_json(path: Path, data: Any):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def ensure_seed_files():
    if not BARBADOS_FILE.exists():
        save_json(
            BARBADOS_FILE,
            {
                "capital": "Bridgetown",
                "parishes": [
                    "Christ Church",
                    "Saint Andrew",
                    "Saint George",
                    "Saint James",
                    "Saint John",
                    "Saint Joseph",
                    "Saint Lucy",
                    "Saint Michael",
                    "Saint Peter",
                    "Saint Philip",
                    "Saint Thomas"
                ],
                "emergency_contacts": {
                    "police": "211",
                    "fire": "311",
                    "ambulance": "511"
                },
                "recipes": {
                    "cou-cou": {
                        "ingredients": ["cornmeal", "okra", "water", "salt", "butter"],
                        "steps": [
                            "Boil sliced okra in water until soft.",
                            "Keep the okra liquid.",
                            "Slowly add cornmeal while stirring.",
                            "Add butter and salt.",
                            "Turn until smooth and firm."
                        ]
                    }
                },
                "transport_notes": {
                    "general": "Public transport includes government buses, minibuses, and ZR vans."
                },
                "hotels": [
                    {
                        "name": "South Gap Hotel",
                        "location": "St. Lawrence Gap, Christ Church",
                        "type": "hotel",
                        "near": ["beach", "restaurants"],
                        "link": "https://example.com/south-gap"
                    },
                    {
                        "name": "Yellow Bird Hotel",
                        "location": "St. Lawrence Gap, Christ Church",
                        "type": "hotel",
                        "near": ["beach", "nightlife"],
                        "link": "https://example.com/yellow-bird"
                    }
                ],
                "events": [
                    {
                        "name": "Oistins Fish Fry",
                        "date": "Friday",
                        "location": "Oistins, Christ Church",
                        "price": "Varies",
                        "link": "https://example.com/oistins"
                    }
                ],
                "jobs": [
                    {
                        "title": "Customer Service Representative",
                        "company": "Island Support Ltd",
                        "location": "Bridgetown",
                        "link": "https://example.com/job-customer-service"
                    }
                ]
            }
        )

    if not CHATS_FILE.exists():
        save_json(CHATS_FILE, [])

    if not MEMORY_FILE.exists():
        save_json(MEMORY_FILE, {})


ensure_seed_files()


# =========================
# DATA ACCESS
# =========================

def get_barbados_data() -> Dict[str, Any]:
    return load_json(BARBADOS_FILE, {})


def get_chats() -> List[Dict[str, Any]]:
    return load_json(CHATS_FILE, [])


def save_chats(chats: List[Dict[str, Any]]):
    save_json(CHATS_FILE, chats)


def get_memory() -> Dict[str, str]:
    return load_json(MEMORY_FILE, {})


def save_memory(memory: Dict[str, str]):
    save_json(MEMORY_FILE, memory)


def find_chat(chat_id: str) -> Optional[Dict[str, Any]]:
    chats = get_chats()
    for chat in chats:
        if chat["id"] == chat_id:
            return chat
    return None


def update_chat(updated_chat: Dict[str, Any]):
    chats = get_chats()
    for i, chat in enumerate(chats):
        if chat["id"] == updated_chat["id"]:
            chats[i] = updated_chat
            save_chats(chats)
            return
    chats.append(updated_chat)
    save_chats(chats)


# =========================
# CHAT MANAGEMENT
# =========================

def create_new_chat() -> Dict[str, Any]:
    now = utc_now()
    chat = {
        "id": str(uuid4()),
        "title": "New Chat",
        "created_at": now,
        "updated_at": now,
        "messages": [
            {
                "role": "assistant",
                "content": "Hi, I'm BIM-CHAT. Ask me anything about Barbados.",
                "timestamp": now
            }
        ]
    }
    chats = get_chats()
    chats.insert(0, chat)
    save_chats(chats)
    return chat


def auto_title_from_first_message(text: str) -> str:
    words = text.strip().split()
    if not words:
        return "New Chat"
    return " ".join(words[:6]).strip().title()


# =========================
# MEMORY
# =========================

def detect_memory_candidates(user_text: str) -> Dict[str, str]:
    text = user_text.lower()
    found = {}

    if "i am a tourist" in text:
        found["user_type"] = "tourist"
    elif "i am a student" in text:
        found["user_type"] = "student"
    elif "i am local" in text or "i'm local" in text:
        found["user_type"] = "local"
    elif "i need a job" in text or "i am looking for a job" in text:
        found["interest"] = "jobs"

    if "dark mode" in text:
        found["theme_preference"] = "dark"
    elif "light mode" in text:
        found["theme_preference"] = "light"

    return found


# =========================
# TOOLS
# =========================

def get_emergency_contacts() -> Dict[str, str]:
    data = get_barbados_data()
    return data.get("emergency_contacts", {})


def get_recipe(dish: str) -> Dict[str, Any]:
    data = get_barbados_data()
    recipes = data.get("recipes", {})
    return recipes.get(dish.lower(), {})


def find_hotels(query: str) -> List[Dict[str, str]]:
    data = get_barbados_data()
    hotels = data.get("hotels", [])
    q = query.lower()
    results = []

    for hotel in hotels:
        haystack = " ".join([
            hotel.get("name", ""),
            hotel.get("location", ""),
            " ".join(hotel.get("near", []))
        ]).lower()
        if any(word in haystack for word in q.split()):
            results.append(hotel)

    return results[:5] if results else hotels[:5]


def find_events(query: str) -> List[Dict[str, str]]:
    data = get_barbados_data()
    events = data.get("events", [])
    q = query.lower()
    results = []

    for event in events:
        haystack = " ".join([
            event.get("name", ""),
            event.get("date", ""),
            event.get("location", "")
        ]).lower()
        if any(word in haystack for word in q.split()):
            results.append(event)

    return results[:5] if results else events[:5]


def find_jobs(query: str) -> List[Dict[str, str]]:
    data = get_barbados_data()
    jobs = data.get("jobs", [])
    q = query.lower()
    results = []

    for job in jobs:
        haystack = " ".join([
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", "")
        ]).lower()
        if any(word in haystack for word in q.split()):
            results.append(job)

    return results[:5] if results else jobs[:5]


def get_transport_info(start: str, end: str) -> Dict[str, str]:
    return {
        "from": start,
        "to": end,
        "method": "Bus or taxi",
        "estimated_time": "45-75 minutes depending on route and traffic",
        "note": "Public transport includes buses, minibuses, and ZR vans."
    }


def convert_to_bbd(amount: float, from_currency: str, to_currency: str = "BBD") -> Dict[str, Any]:
    if from_currency.upper() == "BBD" and to_currency.upper() == "BBD":
        return {
            "amount": amount,
            "from_currency": "BBD",
            "to_currency": "BBD",
            "converted_amount": amount
        }

    if from_currency.upper() == "USD" and to_currency.upper() == "BBD":
        return {
            "amount": amount,
            "from_currency": "USD",
            "to_currency": "BBD",
            "converted_amount": round(amount * 2, 2)
        }

    if from_currency.upper() == "BBD" and to_currency.upper() == "USD":
        return {
            "amount": amount,
            "from_currency": "BBD",
            "to_currency": "USD",
            "converted_amount": round(amount / 2, 2)
        }

    return {
        "amount": amount,
        "from_currency": from_currency.upper(),
        "to_currency": to_currency.upper(),
        "converted_amount": None,
        "note": "Connect a live currency API here for real-time conversion."
    }


def get_barbados_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,wind_speed_10m",
                "timezone": "auto"
            },
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})
        return {
            "temperature": current.get("temperature_2m"),
            "wind_speed": current.get("wind_speed_10m"),
            "units": {"temperature": "°C", "wind_speed": "km/h"}
        }
    except Exception:
        return {
            "temperature": None,
            "wind_speed": None,
            "units": {"temperature": "°C", "wind_speed": "km/h"},
            "note": "Weather API unavailable right now."
        }


# =========================
# IMAGE INTENT
# =========================

def generate_image_from_prompt(prompt: str) -> Dict[str, Any]:
    if not client:
        return {"error": "OPENAI_API_KEY is missing."}
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return {
            "image_url": response.data[0].url,
            "revised_prompt": response.data[0].revised_prompt
        }
    except Exception as e:
        return {"error": str(e)}


# =========================
# INTENT ROUTING
# =========================

def handle_tool_query(message: str) -> Optional[str]:
    text = message.lower()
    data = get_barbados_data()

    if "emergency" in text or "police" in text or "fire" in text or "ambulance" in text:
        contacts = get_emergency_contacts()
        return (
            f"Emergency contacts in Barbados:\n"
            f"- Police: {contacts.get('police', 'N/A')}\n"
            f"- Fire: {contacts.get('fire', 'N/A')}\n"
            f"- Ambulance: {contacts.get('ambulance', 'N/A')}"
        )

    if "capital" in text:
        return f"The capital of Barbados is {data.get('capital', 'Bridgetown')}."

    if "parish" in text:
        parishes = ", ".join(data.get("parishes", []))
        return f"The parishes of Barbados are: {parishes}."

    if "recipe" in text or "cook cou-cou" in text or "how to cook cou-cou" in text or "cou-cou" in text:
        recipe = get_recipe("cou-cou")
        if recipe:
            ingredients = ", ".join(recipe.get("ingredients", []))
            steps = "\n".join([f"{i+1}. {s}" for i, s in enumerate(recipe.get("steps", []))])
            return f"Cou-cou ingredients: {ingredients}\nSteps:\n{steps}"

    if "hotel" in text or "staycation" in text:
        hotels = find_hotels(message)
        if hotels:
            lines = ["Here are some hotel options:"]
            for hotel in hotels:
                lines.append(f"- {hotel['name']} | {hotel['location']} | {hotel['link']}")
            return "\n".join(lines)

    if "event" in text or "this weekend" in text or "crop over" in text:
        events = find_events(message)
        if events:
            lines = ["Here are some event options:"]
            for event in events:
                lines.append(
                    f"- {event['name']} | {event['date']} | {event['location']} | {event['price']} | {event['link']}"
                )
            return "\n".join(lines)

    if "job" in text or "work" in text or "employment" in text:
        jobs = find_jobs(message)
        if jobs:
            lines = ["Here are some job options:"]
            for job in jobs:
                lines.append(
                    f"- {job['title']} at {job['company']} | {job['location']} | {job['link']}"
                )
            return "\n".join(lines)

    if "get to" in text or ("from" in text and "to" in text):
        start = "Unknown"
        end = "Unknown"
        if "from" in text and "to" in text:
            try:
                after_from = message.lower().split("from", 1)[1]
                parts = after_from.split("to", 1)
                start = parts[0].strip(" ?,.").title()
                end = parts[1].strip(" ?,.").title()
            except Exception:
                pass
        elif "to st michael" in text:
            end = "St Michael"

        info = get_transport_info(start, end)
        return (
            f"Travel info:\n"
            f"- From: {info['from']}\n"
            f"- To: {info['to']}\n"
            f"- Method: {info['method']}\n"
            f"- Estimated time: {info['estimated_time']}\n"
            f"- Note: {info['note']}"
        )

    if "convert" in text and "usd" in text:
        amount = 1.0
        for token in text.replace("$", " ").split():
            try:
                amount = float(token)
                break
            except ValueError:
                continue
        result = convert_to_bbd(amount, "USD", "BBD")
        return f"{result['amount']} USD is about {result['converted_amount']} BBD."

    return None


# =========================
# OPENAI
# =========================

SYSTEM_PROMPT = """
You are BIM-CHAT, a Barbados-focused assistant for tourists, locals, students, and job seekers.

Rules:
1. Prefer Barbados-specific helpful answers.
2. Use the provided conversation and memory when useful.
3. Do not invent emergency numbers, prices, dates, addresses, websites, or contacts.
4. If live verification is needed, say so clearly.
5. Keep answers clean, friendly, and practical.
"""


def build_memory_text(memory: Dict[str, str]) -> str:
    if not memory:
        return "No saved memory."
    return "\n".join([f"- {k}: {v}" for k, v in memory.items()])


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image using DALL-E 3 based on a descriptive prompt. Call this whenever the user asks you to draw, create, paint, illustrate, or generate any kind of image or picture.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "A detailed, descriptive prompt for the image to generate."
                    }
                },
                "required": ["prompt"]
            }
        }
    }
]


def call_openai(message: str, chat_messages: List[Dict[str, Any]], memory: Dict[str, str], model: str) -> Dict[str, Any]:
    """Call OpenAI with function calling enabled. Returns dict with 'text' and optional 'image_url'."""
    if not client:
        return {"text": "OPENAI_API_KEY is missing. Add it to your environment to enable AI responses."}

    prompt_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Saved user memory:\n{build_memory_text(memory)}"},
    ]

    for msg in chat_messages[-10:]:
        prompt_messages.append({"role": msg["role"], "content": msg["content"]})

    prompt_messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model=model or DEFAULT_MODEL,
            messages=prompt_messages,
            tools=TOOLS,
            tool_choice="auto"
        )
    except Exception as e:
        return {"text": f"I could not reach OpenAI right now: {e}"}

    choice = response.choices[0]

    # Model wants to generate an image
    if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
        tool_call = choice.message.tool_calls[0]
        if tool_call.function.name == "generate_image":
            import json as _json
            try:
                args = _json.loads(tool_call.function.arguments)
            except Exception:
                args = {"prompt": message}
            result = generate_image_from_prompt(args.get("prompt", message))
            if "error" in result:
                return {"text": f"Sorry, I couldn't generate the image: {result['error']}"}
            return {
                "text": "Here is the image I generated for you!",
                "image_url": result["image_url"]
            }

    return {"text": choice.message.content or "Sorry, I could not generate a reply."}


# =========================
# ROUTES
# =========================

@app.get("/health")
def health():
    return {"status": "ok", "app": "BIM-CHAT API"}


@app.get("/chats")
def list_chats():
    return get_chats()


@app.post("/chats/new", response_model=NewChatResponse)
def new_chat():
    chat = create_new_chat()
    return chat


@app.get("/chats/{chat_id}")
def get_chat(chat_id: str):
    chat = find_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: str):
    chats = get_chats()
    new_chats = [c for c in chats if c["id"] != chat_id]
    save_chats(new_chats)
    return {"success": True}


@app.get("/memory")
def read_memory():
    return get_memory()


@app.post("/memory")
def write_memory(record: MemoryRecord):
    memory = get_memory()
    memory[record.key] = record.value
    save_memory(memory)
    return {"success": True, "memory": memory}


@app.post("/weather")
def weather(payload: WeatherRequest):
    return get_barbados_weather(payload.latitude, payload.longitude)


@app.post("/convert-currency")
def convert_currency(payload: CurrencyRequest):
    return convert_to_bbd(payload.amount, payload.from_currency, payload.to_currency)


@app.post("/generate-image")
def generate_image(payload: ImageRequest):
    if not client:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing.")

    valid_sizes = {"1024x1024", "1792x1024", "1024x1792"}
    size = payload.size if payload.size in valid_sizes else "1024x1024"

    valid_quality = {"standard", "hd"}
    quality = payload.quality if payload.quality in valid_quality else "standard"

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=payload.prompt,
            size=size,
            quality=quality,
            n=1,
        )
        image_url = response.data[0].url
        revised_prompt = response.data[0].revised_prompt
        return {"image_url": image_url, "revised_prompt": revised_prompt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
def chat(payload: ChatRequest):
    chat_obj = find_chat(payload.chat_id)
    if not chat_obj:
        raise HTTPException(status_code=404, detail="Chat not found")

    now = utc_now()
    user_message = {"role": "user", "content": payload.message, "timestamp": now}
    chat_obj["messages"].append(user_message)

    # auto-title from first user message
    if chat_obj["title"] == "New Chat":
        chat_obj["title"] = auto_title_from_first_message(payload.message)

    # save memory candidates
    memory = get_memory()
    memory_updates = detect_memory_candidates(payload.message)
    if memory_updates:
        memory.update(memory_updates)
        save_memory(memory)

    # try local/tool answer first
    local_reply = handle_tool_query(payload.message)
    image_url = None

    if local_reply:
        assistant_text = local_reply
        source = "tool_or_local_data"
    else:
        ai_result = call_openai(
            message=payload.message,
            chat_messages=chat_obj["messages"],
            memory=memory,
            model=payload.model
        )
        assistant_text = ai_result["text"]
        image_url = ai_result.get("image_url")
        source = "dall-e-3" if image_url else "openai"

    assistant_message = {
        "role": "assistant",
        "content": assistant_text,
        "timestamp": utc_now()
    }

    chat_obj["messages"].append(assistant_message)
    chat_obj["updated_at"] = utc_now()
    update_chat(chat_obj)

    response_payload = {
        "chat_id": chat_obj["id"],
        "title": chat_obj["title"],
        "answer": assistant_text,
        "source": source,
        "memory": memory
    }
    if image_url:
        response_payload["image_url"] = image_url

    return response_payload
