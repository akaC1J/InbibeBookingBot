from typing import Dict, List, Set

from inbibe_bot.models import Booking, UserState

# In-memory storage for user states and bookings
user_states: Dict[int, UserState] = {}
bookings: Dict[str, Booking] = {}

# Tracks alternative date/time requests: booking_id -> admin message_id
alt_requests: Dict[str, int] = {}
# Tracks table selection prompt messages in admin group: booking_id -> message_id
table_requests: Dict[str, int] = {}

# Queue of approved (ready) bookings to be delivered via API
not_sent_bookings: List[Booking] = []

actual_tables: list[int] = [1,2,3,4,11,12,13,14,15,16,17,18,21,22,23,24,25]


