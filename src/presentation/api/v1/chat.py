from fastapi import APIRouter

router = APIRouter()


@router.post("/chat", tags=["Chat"])
async def chat_message():
    return {"response": "I am the AI SRE agent. How can I help you today?"}
