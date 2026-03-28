# Twilio outbound call client.
from twilio.rest import Client


TWIML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{websocket_url}" />
  </Connect>
</Response>"""


class TwilioClient:
    # Manages outbound calls via Twilio.

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number

    def make_call(self, to_number: str, websocket_url: str) -> str:
        # Initiate an outbound call streaming to our WebSocket. Returns call SID.
        twiml = TWIML_TEMPLATE.format(websocket_url=websocket_url)
        call = self.client.calls.create(
            to=to_number,
            from_=self.from_number,
            twiml=twiml,
        )
        return call.sid

    def get_call_status(self, call_sid: str) -> str:
        # Get current status of a call.
        call = self.client.calls(call_sid).fetch()
        return call.status

    def end_call(self, call_sid: str) -> None:
        # Terminate a call.
        self.client.calls(call_sid).update(status="completed")
