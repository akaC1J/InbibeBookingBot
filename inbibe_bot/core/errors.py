from __future__ import annotations


class FlowValidationError(ValueError):
    pass


class InvalidTransition(Exception):
    def __init__(self, from_status: str, to_status: str, booking_id: str) -> None:
        super().__init__(
            f"Недопустимый переход {from_status} → {to_status} для заявки {booking_id}"
        )
        self.from_status = from_status
        self.to_status = to_status
        self.booking_id = booking_id


class BookingNotFound(KeyError):
    def __init__(self, booking_id: str) -> None:
        super().__init__(booking_id)
        self.booking_id = booking_id
