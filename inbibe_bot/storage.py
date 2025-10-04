from typing import Dict

from inbibe_bot.models import Booking, UserState

# In-memory storage for user states and bookings
user_states: Dict[int, UserState] = {}
bookings: Dict[str, Booking] = {}

# Tracks alternative date/time requests: booking_id -> admin message_id
alt_requests: Dict[str, int] = {}


