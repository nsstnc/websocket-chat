import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Query, Form, status, Request, Response
from typing import List, Dict
from pydantic import BaseModel

app = FastAPI()

templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        self.active_connections[room_id].remove(websocket)
        if not self.active_connections[room_id]:
            del self.active_connections[room_id]

    async def broadcast(self, room_id: str, message: str):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                await connection.send_text(message)


manager = ConnectionManager()
chat_rooms: Dict[str, List[str]] = {}


class RoomID(BaseModel):
    room_id: str


@app.get("/", response_class=HTMLResponse)
async def get_main(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})


@app.get("/chat/{room_id}", response_class=HTMLResponse)
async def get_chat(request: Request, room_id: str):
    return templates.TemplateResponse("chat.html", {"request": request, "room_id": room_id})


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)

    # Инициализация истории комнаты, если она еще не существует
    if room_id not in chat_rooms:
        chat_rooms[room_id] = []

    try:
        # Отправка истории сообщений при подключении
        for message in chat_rooms[room_id]:
            await websocket.send_text(message)

        # Прием и рассылка сообщений
        while True:
            data = await websocket.receive_text()
            chat_rooms[room_id].append(data)
            await manager.broadcast(room_id, data)
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
