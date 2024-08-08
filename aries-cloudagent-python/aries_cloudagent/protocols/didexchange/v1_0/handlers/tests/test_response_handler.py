from unittest import IsolatedAsyncioTestCase

import pytest

from aries_cloudagent.tests import mock

from ......connections.models import connection_target
from ......connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt
from ......wallet.did_method import SOV, DIDMethods
from ......wallet.key_type import ED25519
from .....trustping.v1_0.messages.ping import Ping
from ...handlers import response_handler as test_module
from ...manager import DIDXManagerError
from ...messages.problem_report import DIDXProblemReport, ProblemReportReason
from ...messages.response import DIDXResponse

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_LABEL = "Label"
TEST_ENDPOINT = "http://localhost"
TEST_IMAGE_URL = "http://aries.ca/images/sample.png"


class TestDIDXResponseHandler(IsolatedAsyncioTestCase):
    def did_doc(self):
        doc = DIDDoc(did=TEST_DID)
        controller = TEST_DID
        ident = "1"
        pk_value = TEST_VERKEY
        pk = PublicKey(
            TEST_DID,
            ident,
            pk_value,
            PublicKeyType.ED25519_SIG_2018,
            controller,
            False,
        )
        doc.set(pk)
        recip_keys = [pk]
        router_keys = []
        service = Service(
            TEST_DID,
            "indy",
            "IndyAgent",
            recip_keys,
            router_keys,
            TEST_ENDPOINT,
        )
        doc.set(service)
        return doc

    async def asyncSetUp(self):
        self.ctx = RequestContext.test_context()
        self.ctx.message_receipt = MessageReceipt()

        self.ctx.profile.context.injector.bind_instance(DIDMethods, DIDMethods())
        wallet = (await self.ctx.session()).wallet
        self.did_info = await wallet.create_local_did(
            method=SOV,
            key_type=ED25519,
        )

        self.did_doc_attach = AttachDecorator.data_base64(self.did_doc().serialize())
        await self.did_doc_attach.data.sign(self.did_info.verkey, wallet)

        self.request = DIDXResponse(
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )

    @pytest.mark.asyncio(scope="module")
    @mock.patch.object(test_module, "DIDXManager")
    async def test_called(self, mock_didx_mgr):
        mock_didx_mgr.return_value.accept_response = mock.CoroutineMock()
        self.ctx.message = DIDXResponse()
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)

        mock_didx_mgr.return_value.accept_response.assert_called_once_with(
            self.ctx.message, self.ctx.message_receipt
        )
        assert not responder.messages

    @pytest.mark.asyncio(scope="module")
    @mock.patch.object(test_module, "DIDXManager")
    async def test_called_auto_ping(self, mock_didx_mgr):
        self.ctx.update_settings({"auto_ping_connection": True})
        mock_didx_mgr.return_value.accept_response = mock.CoroutineMock()
        self.ctx.message = DIDXResponse()
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)

        mock_didx_mgr.return_value.accept_response.assert_called_once_with(
            self.ctx.message, self.ctx.message_receipt
        )
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert isinstance(result, Ping)

    @pytest.mark.asyncio(scope="module")
    @mock.patch.object(test_module, "DIDXManager")
    @mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report(self, mock_conn_target, mock_didx_mgr):
        mock_didx_mgr.return_value.accept_response = mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED.value
            )
        )
        mock_didx_mgr.return_value.manager_error_to_problem_report = mock.CoroutineMock(
            return_value=(
                DIDXProblemReport(
                    description={
                        "en": "test error",
                        "code": ProblemReportReason.RESPONSE_NOT_ACCEPTED.value,
                    }
                ),
                [mock_conn_target],
            )
        )
        self.ctx.message = DIDXResponse()
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, DIDXProblemReport)
            and result.description
            and (
                result.description["code"]
                == ProblemReportReason.RESPONSE_NOT_ACCEPTED.value
            )
        )
        assert target == {"target_list": [mock_conn_target]}

    @pytest.mark.asyncio(scope="module")
    @mock.patch.object(test_module, "DIDXManager")
    @mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc(
        self,
        mock_conn_target,
        mock_didx_mgr,
    ):
        mock_didx_mgr.return_value.accept_response = mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED.value
            )
        )
        mock_didx_mgr.return_value.diddoc_connection_targets = mock.MagicMock(
            return_value=[mock_conn_target]
        )
        mock_didx_mgr.return_value.manager_error_to_problem_report = mock.CoroutineMock(
            return_value=(
                DIDXProblemReport(
                    description={
                        "en": "test error",
                        "code": ProblemReportReason.RESPONSE_NOT_ACCEPTED.value,
                    }
                ),
                [mock_conn_target],
            )
        )
        self.ctx.message = DIDXResponse(
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 1
        result, target = messages[0]
        assert (
            isinstance(result, DIDXProblemReport)
            and result.description
            and (
                result.description["code"]
                == ProblemReportReason.RESPONSE_NOT_ACCEPTED.value
            )
        )
        assert target == {"target_list": [mock_conn_target]}

    @pytest.mark.asyncio(scope="module")
    @mock.patch.object(test_module, "DIDXManager")
    @mock.patch.object(connection_target, "ConnectionTarget")
    async def test_problem_report_did_doc_no_conn_target(
        self,
        mock_conn_target,
        mock_didx_mgr,
    ):
        mock_didx_mgr.return_value.accept_response = mock.CoroutineMock(
            side_effect=DIDXManagerError(
                error_code=ProblemReportReason.RESPONSE_NOT_ACCEPTED.value
            )
        )
        mock_didx_mgr.return_value.diddoc_connection_targets = mock.MagicMock(
            side_effect=DIDXManagerError("no target")
        )
        mock_didx_mgr.return_value.manager_error_to_problem_report = mock.CoroutineMock(
            return_value=(
                DIDXProblemReport(
                    description={
                        "en": "test error",
                        "code": ProblemReportReason.RESPONSE_NOT_ACCEPTED.value,
                    }
                ),
                None,
            )
        )
        self.ctx.message = DIDXResponse(
            did=TEST_DID,
            did_doc_attach=self.did_doc_attach,
        )
        handler_inst = test_module.DIDXResponseHandler()
        responder = MockResponder()
        await handler_inst.handle(self.ctx, responder)
        messages = responder.messages
        assert len(messages) == 0  # need target to add message
