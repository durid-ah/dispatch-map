from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    db_url: str
    env: str
    active_calls_url: str
    user_agent: str
    nominatim_url: str
    geocode_city: str

    def __init__(self):
        self.db_url = os.getenv("DB_URL")
        self.env = os.getenv("ENV")
        self.active_calls_url = os.getenv("ACTIVE_CALLS_URL")
        self.user_agent = os.getenv("USER_AGENT")
        self.nominatim_url = os.getenv(
            "NOMINATIM_URL",
            "http://localhost:8091/search",
        )
        self.geocode_city = os.getenv("GEOCODE_CITY", "Richmond, VA")

config = Config()