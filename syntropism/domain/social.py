import json

import nats
from sqlalchemy.orm import Session

from syntropism.core.genesis import spawn_child_agent
from syntropism.domain.attention import AttentionManager
from syntropism.domain.models import Message
from syntropism.infra.database import SessionLocal


class SocialManager:
    @staticmethod
    def send_message(session: Session, from_id: str, to_id: str, content: str) -> Message:
        message = Message(from_agent_id=from_id, to_agent_id=to_id, content=content)
        session.add(message)
        session.commit()
        return message

    @staticmethod
    def spawn_agent(session: Session, parent_id: str, initial_credits: float, payload: dict = None):
        return spawn_child_agent(session, parent_id, initial_credits, payload)

    async def run_nats(self, nats_url: str = "nats://localhost:4222"):
        nc = await nats.connect(nats_url, connect_timeout=2)

        async def message_handler(msg):
            data = json.loads(msg.data)
            with SessionLocal() as session:
                try:
                    message = self.send_message(session, data["from_id"], data["to_id"], data["content"])
                    await msg.respond(json.dumps({"status": "success", "message_id": message.id}).encode())
                except Exception as e:
                    await msg.respond(json.dumps({"status": "error", "message": str(e)}).encode())

        async def spawn_handler(msg):
            data = json.loads(msg.data)
            with SessionLocal() as session:
                try:
                    child = self.spawn_agent(session, data["parent_id"], data["initial_credits"], data.get("payload"))
                    await msg.respond(
                        json.dumps(
                            {"status": "success", "child_id": child.id, "workspace_id": child.workspace_id}
                        ).encode()
                    )
                except Exception as e:
                    await msg.respond(json.dumps({"status": "error", "message": str(e)}).encode())

        async def prompt_handler(msg):
            data = json.loads(msg.data)
            with SessionLocal() as session:
                try:
                    prompt = AttentionManager.submit_prompt(
                        session, data["agent_id"], data["execution_id"], data["content"], data["bid_amount"]
                    )
                    session.commit()
                    await msg.respond(json.dumps({"status": "success", "prompt_id": prompt.id}).encode())
                except Exception as e:
                    await msg.respond(json.dumps({"status": "error", "message": str(e)}).encode())

        await nc.subscribe("social.message", cb=message_handler)
        await nc.subscribe("social.spawn", cb=spawn_handler)
        await nc.subscribe("human.prompt", cb=prompt_handler)
        return nc
