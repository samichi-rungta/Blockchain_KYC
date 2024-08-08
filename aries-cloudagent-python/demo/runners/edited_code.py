import asyncio
import datetime
import json
import logging
import os
import sys
import time
from uuid import uuid4

from aiohttp import ClientError
from qrcode import QRCode

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runners.agent_container import (  # noqa:E402
    AriesAgent,
    arg_parser,
    create_agent_with_args,
)
from runners.support.agent import (  # noqa:E402
    CRED_FORMAT_INDY,
    CRED_FORMAT_JSON_LD,
    CRED_FORMAT_VC_DI,
    SIG_TYPE_BLS,
)
from runners.support.utils import (  # noqa:E402
    log_msg,
    log_status,
    prompt,
    prompt_loop,
)

CRED_PREVIEW_TYPE = "https://didcomm.org/issue-credential/2.0/credential-preview"
SELF_ATTESTED = os.getenv("SELF_ATTESTED")
TAILS_FILE_COUNT = int(os.getenv("TAILS_FILE_COUNT", 100))

DEMO_EXTRA_AGENT_ARGS = os.getenv("DEMO_EXTRA_AGENT_ARGS")

logging.basicConfig(level=logging.WARNING)
LOGGER = logging.getLogger(__name__)


class FaberAgent(AriesAgent):
    def __init__(
        self,
        ident: str,
        http_port: int,
        admin_port: int,
        no_auto: bool = False,
        endorser_role: str = None,
        revocation: bool = False,
        anoncreds_legacy_revocation: str = None,
        log_file: str = None,
        log_config: str = None,
        log_level: str = None,
        **kwargs,
    ):
        super().__init__(
            ident,
            http_port,
            admin_port,
            prefix="Faber",
            no_auto=no_auto,
            endorser_role=endorser_role,
            revocation=revocation,
            anoncreds_legacy_revocation=anoncreds_legacy_revocation,
            log_file=log_file,
            log_config=log_config,
            log_level=log_level,
            **kwargs,
        )
        self.connection_id = None
        self._connection_ready = None
        self.cred_state = {}
        # TODO define a dict to hold credential attributes
        # based on cred_def_id
        self.cred_attrs = {}

    async def detect_connection(self):
        await self._connection_ready
        self._connection_ready = None

    @property
    def connection_ready(self):
        return self._connection_ready.done() and self._connection_ready.result()

    async def create_connection_invitation(self):
        response = await self.admin_POST("/connections/create-invitation")
        self.connection_id = response["connection_id"]
        self._connection_ready = asyncio.Future()
        self._connection_ready.set_result(True)
        return response["invitation"]

    async def accept_connection_invitation(self, invitation):
        response = await self.admin_POST("/connections/receive-invitation", data=invitation)
        self.connection_id = response["connection_id"]
        self._connection_ready = asyncio.Future()
        self._connection_ready.set_result(True)

    def generate_credential_offer(self, aip, cred_type, cred_def_id, exchange_tracing):
        birth_date_format = "%Y%m%d"
        d = datetime.date.today()
        birth_date = datetime.date(d.year - 20, d.month, d.day)  # Adjust age if needed

        kyc_attributes = {
            "ID": "123456789",
            "Name": "Sam",
            "DOB": birth_date.strftime(birth_date_format),
            "Gender": "Female",
            "Nationality": "Nepali",
            "Country": "Nepal",
            "City": "Lalitpur",
            "Street": "Sanepa",
            "PhoneNumber": "1234567890",
            "Email": "sam@gmail.com",
            "SchoolName": "FLAME",
            "LevelDegree": "Bachelor's",
            "Year": "2022",
            "CompanyName": "F1 Soft",
            "Position": "Engineer",
            "YearStarted": "2024",
            "FatherName": "Rishab",
            "MotherName": "Shejal",
            "GrandfatherName": "Om",
            "DocumentHashes": "hash1,hash2,hash3"
        }
                     
        if aip == 10:
            self.cred_attrs[cred_def_id] = kyc_attributes

            cred_preview = {
                "@type": CRED_PREVIEW_TYPE,
                "attributes": [
                    {"name": n, "value": v}
                    for (n, v) in self.cred_attrs[cred_def_id].items()
                ],
            }
            offer_request = {
                "connection_id": self.connection_id,
                "cred_def_id": cred_def_id,
                "comment": f"Offer on cred def id {cred_def_id}",
                "auto_remove": False,
                "credential_preview": cred_preview,
                "trace": exchange_tracing,
            }
            return offer_request

        elif aip == 20:
            if cred_type == CRED_FORMAT_INDY:
                self.cred_attrs[cred_def_id] = kyc_attributes

                cred_preview = {
                    "@type": CRED_PREVIEW_TYPE,
                    "attributes": [
                        {"name": n, "value": v}
                        for (n, v) in self.cred_attrs[cred_def_id].items()
                    ],
                }
                offer_request = {
                    "connection_id": self.connection_id,
                    "comment": f"Offer on cred def id {cred_def_id}",
                    "auto_remove": False,
                    "credential_preview": cred_preview,
                    "filter": {"indy": {"cred_def_id": cred_def_id}},
                    "trace": exchange_tracing,
                }
                return offer_request

            elif cred_type == CRED_FORMAT_VC_DI:
                self.cred_attrs[cred_def_id] = kyc_attributes

                cred_preview = {
                    "@type": CRED_PREVIEW_TYPE,
                    "attributes": [
                        {"name": n, "value": v}
                        for (n, v) in self.cred_attrs[cred_def_id].items()
                    ],
                }
                offer_request = {
                    "connection_id": self.connection_id,
                    "comment": f"Offer on cred def id {cred_def_id}",
                    "auto_remove": False,
                    "credential_preview": cred_preview,
                    "filter": {"vc_di": {"cred_def_id": cred_def_id}},
                    "trace": exchange_tracing,
                }
                return offer_request

            elif cred_type == CRED_FORMAT_JSON_LD:
                offer_request = {
                    "connection_id": self.connection_id,
                    "filter": {
                        "ld_proof": {
                            "credential": {
                                "@context": [
                                    "https://www.w3.org/2018/credentials/v1",
                                    "https://w3id.org/citizenship/v1",
                                    "https://w3id.org/security/bbs/v1",
                                ],
                                "type": [
                                    "VerifiableCredential",
                                    "PermanentResident",
                                ],
                                "id": "https://credential.example.com/residents/1234567890",
                                "issuer": self.did,
                                "issuanceDate": "2020-01-01T12:00:00Z",
                                "credentialSubject": {
                                    "type": ["PermanentResident"],
                                    "givenName": "Sam",
                                    "familyName": "Rungta",
                                    "gender": "Female",
                                    "birthCountry": "Nepal",
                                    "birthDate": "2004-07-17",
                                },
                            },
                            "options": {"proofType": SIG_TYPE_BLS},
                        }
                    },
                }
                return offer_request

            else:
                raise Exception(f"Error invalid credential type: {self.cred_type}")

        else:
            raise Exception(f"Error invalid AIP level: {self.aip}")


    def generate_proof_request_web_request(
        self, aip, cred_type, revocation, exchange_tracing, connectionless=False
    ):
        age = 18
        d = datetime.date.today()
        birth_date = datetime.date(d.year - age, d.month, d.day)
        birth_date_format = "%Y%m%d"
        if aip == 10:
            req_attrs = [
                {
                    "name": "ID",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "Name",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "DOB",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "Gender",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "Nationality",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "Country",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "City",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "Street",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "PhoneNumber",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "Email",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "SchoolName",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "LevelDegree",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "Year",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "CompanyName",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "Position",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "YearStarted",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "FatherName",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "MotherName",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "GrandfatherName",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
                {
                    "name": "DocumentHashes",
                    "restrictions": [{"schema_name": "kyc schema"}],
                },
            ]
            if revocation:
                req_attrs.append(
                    {
                        "name": "DocumentHashes",
                        "restrictions": [{"schema_name": "kyc schema"}],
                        "non_revoked": {"to": int(time.time() - 1)},
                    }
                )
            else:
                req_attrs.append(
                    {
                        "name": "DocumentHashes",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    }
                )
            if SELF_ATTESTED:
                # test self-attested claims
                req_attrs.append(
                    {"name": "self_attested_thing"},
                )
            req_preds = [
                # test zero-knowledge proofs
                {
                    "name": "birthdate_dateint",
                    "p_type": "<=",
                    "p_value": int(birth_date.strftime(birth_date_format)),
                    "restrictions": [{"schema_name": "kyc schema"}],
                }
            ]
            indy_proof_request = {
                "name": "Proof of KYC",
                "version": "1.0",
                "requested_attributes": {
                    f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
                },
                "requested_predicates": {
                    f"0_{req_pred['name']}_GE_uuid": req_pred for req_pred in req_preds
                },
            }

            if revocation:
                indy_proof_request["non_revoked"] = {"to": int(time.time())}

            proof_request_web_request = {
                "proof_request": indy_proof_request,
                "trace": exchange_tracing,
            }
            if not connectionless:
                proof_request_web_request["connection_id"] = self.connection_id
            return proof_request_web_request

        elif aip == 20:
            if cred_type == CRED_FORMAT_INDY:
                req_attrs = [
                    {
                        "name": "ID",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "Name",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "DOB",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "Gender",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "Nationality",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "Country",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "City",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "Street",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "PhoneNumber",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "Email",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "SchoolName",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "LevelDegree",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "Year",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "CompanyName",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "Position",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "YearStarted",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "FatherName",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "MotherName",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "GrandfatherName",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                    {
                        "name": "DocumentHashes",
                        "restrictions": [{"schema_name": "kyc schema"}],
                    },
                ]
                if revocation:
                    req_attrs.append(
                        {
                            "name": "DocumentHashes",
                            "restrictions": [{"schema_name": "kyc schema"}],
                            "non_revoked": {"to": int(time.time() - 1)},
                        }
                    )
                else:
                    req_attrs.append(
                        {
                            "name": "DocumentHashes",
                            "restrictions": [{"schema_name": "kyc schema"}],
                        }
                    )
                if SELF_ATTESTED:
                    # test self-attested claims
                    req_attrs.append(
                        {"name": "self_attested_thing"},
                    )
                req_preds = [
                    # test zero-knowledge proofs
                    {
                        "name": "birthdate_dateint",
                        "p_type": "<=",
                        "p_value": int(birth_date.strftime(birth_date_format)),
                        "restrictions": [{"schema_name": "kyc schema"}],
                    }
                ]
                indy_proof_request = {
                    "name": "Proof of KYC",
                    "version": "1.0",
                    "requested_attributes": {
                        f"0_{req_attr['name']}_uuid": req_attr for req_attr in req_attrs
                    },
                    "requested_predicates": {
                        f"0_{req_pred['name']}_GE_uuid": req_pred for req_pred in req_preds
                    },
                }

                if revocation:
                    indy_proof_request["non_revoked"] = {"to": int(time.time())}

                proof_request_web_request = {
                    "presentation_request": {"indy": indy_proof_request},
                    "trace": exchange_tracing,
                }
                if not connectionless:
                    proof_request_web_request["connection_id"] = self.connection_id
                return proof_request_web_request

            elif cred_type == CRED_FORMAT_VC_DI:
                proof_request_web_request = {
                    "comment": "Test proof request for VC-DI format",
                    "presentation_request": {
                        "dif": {
                            "options": {
                                "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                                "domain": "4jt78h47fh47",
                            },
                            "presentation_definition": {
                                "id": "5591656f-5b5d-40f8-ab5c-9041c8e3a6a0",
                                "name": "KYC Verification",
                                "purpose": "We need to verify your KYC information",
                                "input_descriptors": [
                                    {
                                        "id": "kyc-verification",
                                        "name": "KYC Verification",
                                        "purpose": "We want to verify your KYC details",
                                        "schema": [
                                            {
                                                "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
                                            }
                                        ],
                                        "constraints": {
                                            "statuses": {
                                                "active": {"directive": "disallowed"}
                                            },
                                            "limit_disclosure": "required",
                                            "fields": [
                                                {
                                                    "path": ["$.issuer"],
                                                    "filter": {
                                                        "type": "string",
                                                        "const": self.did,
                                                    },
                                                },
                                                {"path": ["$.credentialSubject.name"]},
                                                {"path": ["$.credentialSubject.DOB"]},
                                                {"path": ["$.credentialSubject.Gender"]},
                                                {"path": ["$.credentialSubject.Nationality"]},
                                                {"path": ["$.credentialSubject.Country"]},
                                                {"path": ["$.credentialSubject.City"]},
                                                {"path": ["$.credentialSubject.Street"]},
                                                {"path": ["$.credentialSubject.PhoneNumber"]},
                                                {"path": ["$.credentialSubject.Email"]},
                                                {"path": ["$.credentialSubject.SchoolName"]},
                                                {"path": ["$.credentialSubject.LevelDegree"]},
                                                {"path": ["$.credentialSubject.Year"]},
                                                {"path": ["$.credentialSubject.CompanyName"]},
                                                {"path": ["$.credentialSubject.Position"]},
                                                {"path": ["$.credentialSubject.YearStarted"]},
                                                {"path": ["$.credentialSubject.FatherName"]},
                                                {"path": ["$.credentialSubject.MotherName"]},
                                                {"path": ["$.credentialSubject.GrandfatherName"]},
                                                {
                                                    "path": ["$.credentialSubject.birthdate_dateint"],
                                                    "predicate": "preferred",
                                                    "filter": {
                                                        "type": "number",
                                                        "maximum": int(birth_date.strftime(birth_date_format)),
                                                    },
                                                },
                                            ],
                                        },
                                    }
                                ],
                                "format": {
                                    "di_vc": {
                                        "proof_type": ["DataIntegrityProof"],
                                        "cryptosuite": [
                                            "anoncreds-2023",
                                            "eddsa-rdfc-2022",
                                        ],
                                    }
                                },
                            },
                        },
                    },
                }

                if revocation:
                    proof_request_web_request["presentation_request"]["dif"][
                        "presentation_definition"
                    ]["input_descriptors"][0]["constraints"]["statuses"]["active"][
                        "directive"
                    ] = "required"
                if not connectionless:
                    proof_request_web_request["connection_id"] = self.connection_id
                return proof_request_web_request

            elif cred_type == CRED_FORMAT_JSON_LD:
                proof_request_web_request = {
                    "comment": "test proof request for json-ld",
                    "presentation_request": {
                        "dif": {
                            "options": {
                                "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
                                "domain": "4jt78h47fh47",
                            },
                            "presentation_definition": {
                                "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
                                "format": {"ldp_vp": {"proof_type": [SIG_TYPE_BLS]}},
                                "input_descriptors": [
                                    {
                                        "id": "kyc_input_1",
                                        "name": "KYC Credential",
                                        "schema": [
                                            {
                                                "uri": "https://www.w3.org/2018/credentials#VerifiableCredential"
                                            },
                                            {
                                                "uri": "https://w3id.org/citizenship#PermanentResident"
                                            },
                                        ],
                                        "constraints": {
                                            "limit_disclosure": "required",
                                            "is_holder": [
                                                {
                                                    "directive": "required",
                                                    "field_id": [
                                                        "1f44d55f-f161-4938-a659-f8026467f126"
                                                    ],
                                                }
                                            ],
                                            "fields": [
                                                {
                                                    "id": "1f44d55f-f161-4938-a659-f8026467f126",
                                                    "path": ["$.credentialSubject.familyName"],
                                                    "purpose": "The claim must be from one of the specified person",
                                                    "filter": {"const": "SMITH"},
                                                },
                                                {
                                                    "path": ["$.credentialSubject.givenName"],
                                                    "purpose": "The claim must be from one of the specified person",
                                                },
                                            ],
                                        },
                                    }
                                ],
                            },
                        }
                    },
                }
                if not connectionless:
                    proof_request_web_request["connection_id"] = self.connection_id
                return proof_request_web_request

            else:
                raise Exception(f"Error invalid credential type: {self.cred_type}")

        else:
            raise Exception(f"Error invalid AIP level: {self.aip}")



async def main(args):
    extra_args = None
    if DEMO_EXTRA_AGENT_ARGS:
        extra_args = json.loads(DEMO_EXTRA_AGENT_ARGS)
        print("Got extra args:", extra_args)
    faber_agent = await create_agent_with_args(
        args,
        ident="faber",
        extra_args=extra_args,
    )

    try:
        log_status(
            "#1 Provision an agent and wallet, get back configuration details"
            + (
                f" (Wallet type: {faber_agent.wallet_type})"
                if faber_agent.wallet_type
                else ""
            )
        )
        agent = FaberAgent(
            "faber.agent",
            faber_agent.start_port,
            faber_agent.start_port + 1,
            genesis_data=faber_agent.genesis_txns,
            genesis_txn_list=faber_agent.genesis_txn_list,
            no_auto=faber_agent.no_auto,
            tails_server_base_url=faber_agent.tails_server_base_url,
            revocation=faber_agent.revocation,
            timing=faber_agent.show_timing,
            multitenant=faber_agent.multitenant,
            mediation=faber_agent.mediation,
            wallet_type=faber_agent.wallet_type,
            seed=faber_agent.seed,
            aip=faber_agent.aip,
            endorser_role=faber_agent.endorser_role,
            anoncreds_legacy_revocation=faber_agent.anoncreds_legacy_revocation,
            log_file=faber_agent.log_file,
            log_config=faber_agent.log_config,
            log_level=faber_agent.log_level,
            reuse_connections=faber_agent.reuse_connections,
            multi_use_invitations=faber_agent.multi_use_invitations,
            public_did_connections=faber_agent.public_did_connections,
            extra_args=extra_args,
        )

        faber_schema_name = "kyc schema"
        faber_schema_attrs = [
            "ID",
            "Name",
            "DOB",
            "Gender",
            "Nationality",
            "Country",
            "City",
            "Street",
            "PhoneNumber",
            "Email",
            "SchoolName",
            "LevelDegree",
            "Year",
            "CompanyName",
            "Position",
            "YearStarted",
            "FatherName",
            "MotherName",
            "GrandfatherName",
            "DocumentHashes"
        ]
        if faber_agent.cred_type in [CRED_FORMAT_INDY, CRED_FORMAT_VC_DI]:
            faber_agent.public_did = True
            await faber_agent.initialize(
                the_agent=agent,
                schema_name=faber_schema_name,
                schema_attrs=faber_schema_attrs,
                create_endorser_agent=(
                    (faber_agent.endorser_role == "author")
                    if faber_agent.endorser_role
                    else False
                ),
            )
        elif faber_agent.cred_type in [
            CRED_FORMAT_JSON_LD,
        ]:
            faber_agent.public_did = True
            await faber_agent.initialize(the_agent=agent)
        else:
            raise Exception("Invalid credential type:" + faber_agent.cred_type)

        # generate an invitation for Alice
        await faber_agent.generate_invitation(
            display_qr=True,
            reuse_connections=faber_agent.reuse_connections,
            multi_use_invitations=faber_agent.multi_use_invitations,
            public_did_connections=faber_agent.public_did_connections,
            wait=True,
        )

        exchange_tracing = False
        options = "    (1) Issue Credential\n"
        if faber_agent.cred_type in [
            CRED_FORMAT_INDY,
            CRED_FORMAT_VC_DI,
        ]:
            options += "    (1a) Set Credential Type (%CRED_TYPE%)\n"
        options += (
            "    (2) Send Proof Request\n"
            "    (2a) Send *Connectionless* Proof Request (requires a Mobile client)\n"
            "    (3) Send Message\n"
            "    (4) Create New Invitation\n"
        )
        if faber_agent.revocation:
            options += (
                "    (5) Revoke Credential\n"
                "    (6) Publish Revocations\n"
                "    (7) Rotate Revocation Registry\n"
                "    (8) List Revocation Registries\n"
            )
        if faber_agent.endorser_role and faber_agent.endorser_role == "author":
            options += "    (D) Set Endorser's DID\n"
        if faber_agent.multitenant:
            options += "    (W) Create and/or Enable Wallet\n"
            options += "    (U) Upgrade wallet to anoncreds \n"
        options += "    (T) Toggle tracing on credential/proof exchange\n"
        options += "    (X) Exit?\n[1/2/3/4/{}{}T/X] ".format(
            "5/6/7/8/" if faber_agent.revocation else "",
            "W/" if faber_agent.multitenant else "",
        )

        upgraded_to_anoncreds = False
        async for option in prompt_loop(
            options.replace("%CRED_TYPE%", faber_agent.cred_type)
        ):
            if option is not None:
                option = option.strip()

            # Anoncreds has different endpoints for revocation
            is_anoncreds = False
            if (
                faber_agent.agent.__dict__["wallet_type"] == "askar-anoncreds"
                or upgraded_to_anoncreds
            ):
                is_anoncreds = True

            if option is None or option in "xX":
                break

            elif option in "dD" and faber_agent.endorser_role:
                endorser_did = await prompt("Enter Endorser's DID: ")
                await faber_agent.agent.admin_POST(
                    f"/transactions/{faber_agent.agent.connection_id}/set-endorser-info",
                    params={"endorser_did": endorser_did},
                )

            elif option in "wW" and faber_agent.multitenant:
                target_wallet_name = await prompt("Enter wallet name: ")
                include_subwallet_webhook = await prompt(
                    "(Y/N) Create sub-wallet webhook target: "
                )
                if include_subwallet_webhook.lower() == "y":
                    created = await faber_agent.agent.register_or_switch_wallet(
                        target_wallet_name,
                        webhook_port=faber_agent.agent.get_new_webhook_port(),
                        public_did=True,
                        mediator_agent=faber_agent.mediator_agent,
                        endorser_agent=faber_agent.endorser_agent,
                        taa_accept=faber_agent.taa_accept,
                    )
                else:
                    created = await faber_agent.agent.register_or_switch_wallet(
                        target_wallet_name,
                        public_did=True,
                        mediator_agent=faber_agent.mediator_agent,
                        endorser_agent=faber_agent.endorser_agent,
                        cred_type=faber_agent.cred_type,
                        taa_accept=faber_agent.taa_accept,
                    )
                # create a schema and cred def for the new wallet
                # TODO check first in case we are switching between existing wallets
                if created:
                    # TODO this fails because the new wallet doesn't get a public DID
                    await faber_agent.create_schema_and_cred_def(
                        schema_name=faber_schema_name,
                        schema_attrs=faber_schema_attrs,
                    )

            elif option in "tT":
                exchange_tracing = not exchange_tracing
                log_msg(
                    ">>> Credential/Proof Exchange Tracing is {}".format(
                        "ON" if exchange_tracing else "OFF"
                    )
                )

            elif option == "1a":
                new_cred_type = await prompt(
                    "Enter credential type ({}, {}): ".format(
                        CRED_FORMAT_INDY,
                        CRED_FORMAT_VC_DI,
                    )
                )
                if new_cred_type in [
                    CRED_FORMAT_INDY,
                    CRED_FORMAT_VC_DI,
                ]:
                    faber_agent.set_cred_type(new_cred_type)
                else:
                    log_msg("Not a valid credential type.")

            elif option == "1":
                log_status("#13 Issue credential offer to X")

                if faber_agent.aip == 10:
                    offer_request = faber_agent.agent.generate_credential_offer(
                        faber_agent.aip, None, faber_agent.cred_def_id, exchange_tracing
                    )
                    await faber_agent.agent.admin_POST(
                        "/issue-credential/send-offer", offer_request
                    )

                elif faber_agent.aip == 20:
                    if faber_agent.cred_type == CRED_FORMAT_INDY:
                        offer_request = faber_agent.agent.generate_credential_offer(
                            faber_agent.aip,
                            faber_agent.cred_type,
                            faber_agent.cred_def_id,
                            exchange_tracing,
                        )

                    elif faber_agent.cred_type == CRED_FORMAT_JSON_LD:
                        offer_request = faber_agent.agent.generate_credential_offer(
                            faber_agent.aip,
                            faber_agent.cred_type,
                            None,
                            exchange_tracing,
                        )

                    elif faber_agent.cred_type == CRED_FORMAT_VC_DI:
                        offer_request = faber_agent.agent.generate_credential_offer(
                            faber_agent.aip,
                            faber_agent.cred_type,
                            faber_agent.cred_def_id,
                            exchange_tracing,
                        )

                    else:
                        raise Exception(
                            f"Error invalid credential type: {faber_agent.cred_type}"
                        )

                    await faber_agent.agent.admin_POST(
                        "/issue-credential-2.0/send-offer", offer_request
                    )

                else:
                    raise Exception(f"Error invalid AIP level: {faber_agent.aip}")

            elif option == "2":
                try:
                    log_status("#20 Request proof of KYC from Alice")

                    # Debugging: Check the connection ID
                    if not hasattr(faber_agent, 'connection_id') or not faber_agent.connection_id:
                        log_msg("Connection ID is not set or not found.")
                        continue

                    log_msg(f"Using connection ID: {faber_agent.connection_id}")

                    proof_attrs = [
                        {
                            "name": "ID",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Name",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "DOB",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Gender",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Nationality",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Country",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "City",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Street",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "PhoneNumber",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Email",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "SchoolName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "LevelDegree",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Year",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "CompanyName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Position",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "YearStarted",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "FatherName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "MotherName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "GrandfatherName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "DocumentHashes",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                    ]
                    if faber_agent.revocation:
                        proof_attrs.append(
                            {
                                "name": "revocation_reg_id",
                                "restrictions": [{"schema_name": faber_schema_name}],
                            }
                        )
                    proof_predicates = []

                    if faber_agent.aip == 10:
                        proof_request_web_request = {
                            "connection_id": faber_agent.connection_id,
                            "proof_request": {
                                "name": "Proof of KYC",
                                "version": "1.0",
                                "requested_attributes": {
                                    f"0_{attr['name']}_uuid": attr
                                    for attr in proof_attrs
                                },
                                "requested_predicates": {
                                    f"0_{pred['name']}_GE_uuid": pred
                                    for pred in proof_predicates
                                },
                                "nonce": str(uuid4().int),
                            },
                            "trace": exchange_tracing,
                        }
                        await faber_agent.agent.admin_POST(
                            "/present-proof/send-request", proof_request_web_request
                        )

                    elif faber_agent.aip == 20:
                        indy_proof_request = {
                            "name": "Proof of KYC",
                            "version": "1.0",
                            "requested_attributes": {
                                f"0_{attr['name']}_uuid": attr
                                for attr in proof_attrs
                            },
                            "requested_predicates": {
                                f"0_{pred['name']}_GE_uuid": pred
                                for pred in proof_predicates
                            },
                        }
                        request = {
                            "connection_id": faber_agent.connection_id,
                            "presentation_request": {
                                "indy": indy_proof_request
                            },
                            "trace": exchange_tracing,
                        }
                        await faber_agent.agent.admin_POST(
                            "/present-proof-2.0/send-request", request
                        )
                except Exception as e:
                    log_msg(f"Exception occurred while requesting proof: {e}")


            elif option == "2a":
                try:
                    log_status("#20 Request *connectionless* proof of KYC from Alice")
                    proof_attrs = [
                        {
                            "name": "ID",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Name",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "DOB",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Gender",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Nationality",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Country",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "City",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Street",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "PhoneNumber",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Email",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "SchoolName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "LevelDegree",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Year",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "CompanyName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "Position",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "YearStarted",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "FatherName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "MotherName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "GrandfatherName",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                        {
                            "name": "DocumentHashes",
                            "restrictions": [{"schema_name": faber_schema_name}],
                        },
                    ]
                    if faber_agent.revocation:
                        proof_attrs.append(
                            {
                                "name": "revocation_reg_id",
                                "restrictions": [{"schema_name": faber_schema_name}],
                            }
                        )
                    proof_predicates = []

                    if faber_agent.aip == 10:
                        proof_request_web_request = {
                            "proof_request": {
                                "name": "Proof of KYC",
                                "version": "1.0",
                                "requested_attributes": {
                                    f"0_{attr['name']}_uuid": attr
                                    for attr in proof_attrs
                                },
                                "requested_predicates": {
                                    f"0_{pred['name']}_GE_uuid": pred
                                    for pred in proof_predicates
                                },
                                "nonce": str(uuid4().int),
                            },
                            "trace": exchange_tracing,
                        }
                        resp = await faber_agent.agent.admin_POST(
                            "/present-proof/create-request", proof_request_web_request
                        )
                        pres_req_id = resp["presentation_exchange_id"]
                        qr = QRCode(string=resp["presentation_request"]["@id"])
                        qr.print_ascii(invert=True)
                        log_msg(
                            "Presentation request QR code:",
                            resp["presentation_request"]["@id"],
                        )

                    elif faber_agent.aip == 20:
                        indy_proof_request = {
                            "name": "Proof of KYC",
                            "version": "1.0",
                            "requested_attributes": {
                                f"0_{attr['name']}_uuid": attr
                                for attr in proof_attrs
                            },
                            "requested_predicates": {
                                f"0_{pred['name']}_GE_uuid": pred
                                for pred in proof_predicates
                            },
                        }
                        request = {
                            "presentation_request": {
                                "indy": indy_proof_request
                            },
                            "trace": exchange_tracing,
                        }
                        resp = await faber_agent.agent.admin_POST(
                            "/present-proof-2.0/create-request", request
                        )
                        pres_req_id = resp["pres_ex_id"]
                        qr = QRCode(string=resp["presentation_request"]["@id"])
                        qr.print_ascii(invert=True)
                        log_msg(
                            "Presentation request QR code:",
                            resp["presentation_request"]["@id"],
                        )
                except Exception as e:
                    log_msg(f"Exception occurred while requesting connectionless proof: {e}")


            elif option == "3":
                msg = await prompt("Enter message: ")
                await faber_agent.agent.admin_POST(
                    f"/connections/{faber_agent.connection_id}/send-message",
                    {"content": msg},
                )

            elif option == "4":
                log_msg(
                    "Creating a new invitation, please receive "
                    "and accept this invitation using Alice agent"
                )
                await faber_agent.generate_invitation(
                    display_qr=True,
                    reuse_connections=faber_agent.reuse_connections,
                    multi_use_invitations=faber_agent.multi_use_invitations,
                    public_did_connections=faber_agent.public_did_connections,
                    wait=True,
                )

            elif option == "5" and faber_agent.revocation:
                rev_reg_id = (await prompt("Enter revocation registry ID: ")).strip()
                cred_rev_id = (await prompt("Enter credential revocation ID: ")).strip()
                publish = (
                    await prompt("Publish now? [Y/N]: ", default="N")
                ).strip() in "yY"

                try:
                    endpoint = (
                        "/anoncreds/revocation/revoke"
                        if is_anoncreds
                        else "/revocation/revoke"
                    )
                    await faber_agent.agent.admin_POST(
                        endpoint,
                        {
                            "rev_reg_id": rev_reg_id,
                            "cred_rev_id": cred_rev_id,
                            "publish": publish,
                            "connection_id": faber_agent.agent.connection_id,
                            # leave out thread_id, let aca-py generate
                            # "thread_id": "12345678-4444-4444-4444-123456789012",
                            "comment": "Revocation reason goes here ...",
                        },
                    )
                except ClientError:
                    pass

            elif option == "6" and faber_agent.revocation:
                try:
                    endpoint = (
                        "/anoncreds/revocation/publish-revocations"
                        if is_anoncreds
                        else "/revocation/publish-revocations"
                    )
                    resp = await faber_agent.agent.admin_POST(endpoint, {})
                    faber_agent.agent.log(
                        "Published revocations for {} revocation registr{} {}".format(
                            len(resp["rrid2crid"]),
                            "y" if len(resp["rrid2crid"]) == 1 else "ies",
                            json.dumps(list(resp["rrid2crid"]), indent=4),
                        )
                    )
                except ClientError:
                    pass
            elif option == "7" and faber_agent.revocation:
                try:
                    endpoint = (
                        f"/anoncreds/revocation/active-registry/{faber_agent.cred_def_id}/rotate"
                        if is_anoncreds
                        else f"/revocation/active-registry/{faber_agent.cred_def_id}/rotate"
                    )
                    resp = await faber_agent.agent.admin_POST(
                        endpoint,
                        {},
                    )
                    faber_agent.agent.log(
                        "Rotated registries for {}. Decommissioned Registries: {}".format(
                            faber_agent.cred_def_id,
                            json.dumps(list(resp["rev_reg_ids"]), indent=4),
                        )
                    )
                except ClientError:
                    pass
            elif option == "8" and faber_agent.revocation:
                if is_anoncreds:
                    endpoint = "/anoncreds/revocation/registries"
                    states = [
                        "finished",
                        "failed",
                        "action",
                        "wait",
                        "decommissioned",
                        "full",
                    ]
                    default_state = "finished"
                else:
                    endpoint = "/revocation/registries/created"
                    states = [
                        "init",
                        "generated",
                        "posted",
                        "active",
                        "full",
                        "decommissioned",
                    ]
                    default_state = "active"
                state = (
                    await prompt(
                        f"Filter by state: {states}: ",
                        default=default_state,
                    )
                ).strip()
                if state not in states:
                    state = "active"
                try:
                    resp = await faber_agent.agent.admin_GET(
                        endpoint,
                        params={"state": state},
                    )
                    faber_agent.agent.log(
                        "Registries (state = '{}'): {}".format(
                            state,
                            json.dumps(list(resp["rev_reg_ids"]), indent=4),
                        )
                    )
                except ClientError:
                    pass
            elif option in "uU" and faber_agent.multitenant:
                log_status("Upgrading wallet to anoncreds. Wait a couple seconds...")
                await faber_agent.agent.admin_POST(
                    "/anoncreds/wallet/upgrade",
                    params={"wallet_name": faber_agent.agent.wallet_name},
                )
                upgraded_to_anoncreds = True
                await asyncio.sleep(2.0)

        if faber_agent.show_timing:
            timing = await faber_agent.agent.fetch_timing()
            if timing:
                for line in faber_agent.agent.format_timing(timing):
                    log_msg(line)

    finally:
        terminated = await faber_agent.terminate()

    await asyncio.sleep(0.1)

    if not terminated:
        os._exit(1)


if __name__ == "__main__":
    parser = arg_parser(ident="faber", port=8020)
    args = parser.parse_args()

    ENABLE_PYDEVD_PYCHARM = os.getenv("ENABLE_PYDEVD_PYCHARM", "").lower()
    ENABLE_PYDEVD_PYCHARM = ENABLE_PYDEVD_PYCHARM and ENABLE_PYDEVD_PYCHARM not in (
        "false",
        "0",
    )
    PYDEVD_PYCHARM_HOST = os.getenv("PYDEVD_PYCHARM_HOST", "localhost")
    PYDEVD_PYCHARM_CONTROLLER_PORT = int(
        os.getenv("PYDEVD_PYCHARM_CONTROLLER_PORT", 5001)
    )

    if ENABLE_PYDEVD_PYCHARM:
        try:
            import pydevd_pycharm

            print(
                "Faber remote debugging to "
                f"{PYDEVD_PYCHARM_HOST}:{PYDEVD_PYCHARM_CONTROLLER_PORT}"
            )
            pydevd_pycharm.settrace(
                host=PYDEVD_PYCHARM_HOST,
                port=PYDEVD_PYCHARM_CONTROLLER_PORT,
                stdoutToServer=True,
                stderrToServer=True,
                suspend=False,
            )
        except ImportError:
            print("pydevd_pycharm library was not found")

    try:
        asyncio.get_event_loop().run_until_complete(main(args))
    except KeyboardInterrupt:
        os._exit(1)
