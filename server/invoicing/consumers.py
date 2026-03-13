import asyncio

from channels.consumer import AsyncConsumer


class InvoicingConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        print("connected", event)
        await self.send(
            {
                "type": "websocket.accept",
            }
        )
        await self.channel_layer.group_add("chat", self.channel_name)
        for i in range(1, 4):
            await self.send(
                {
                    "type": "websocket.send",
                    "text": f"Hello, from websocket! - {i}",
                }
            )
            await asyncio.sleep(1)

    async def websocket_receive(self, event):
        print("receive", event)
        await self.channel_layer.group_send(
            "chat",
            {
                "type": "chat.message",
                "text": event["text"],
            },
        )

    async def websocket_disconnect(self, event):
        print("disconnected", event)

    async def chat_message(self, event):
        print("chat_message", event)
        await self.send(
            {
                "type": "websocket.send",
                "text": event["text"],
            }
        )


