from unittest import TestCase

from ...valid import UUID4_EXAMPLE
from ..transport_decorator import TransportDecorator


class TestTransportDecorator(TestCase):
    def test_serialize_load(self):
        deco = TransportDecorator(
            return_route="all",
            return_route_thread=UUID4_EXAMPLE,
            queued_message_count=23,
        )

        assert deco.return_route == "all"
        assert deco.return_route_thread == UUID4_EXAMPLE
        assert deco.queued_message_count == 23

        dumped = deco.serialize()
        loaded = TransportDecorator.deserialize(dumped)
