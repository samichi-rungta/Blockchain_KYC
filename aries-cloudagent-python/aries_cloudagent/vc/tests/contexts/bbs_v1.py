BBS_V1 = {
    "@context": {
        "@version": 1.1,
        "id": "@id",
        "type": "@type",
        "BbsBlsSignature2020": {
            "@id": "https://w3id.org/security#BbsBlsSignature2020",
            "@context": {
                "@version": 1.1,
                "@protected": True,
                "id": "@id",
                "type": "@type",
                "challenge": "https://w3id.org/security#challenge",
                "created": {
                    "@id": "http://purl.org/dc/terms/created",
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                },
                "domain": "https://w3id.org/security#domain",
                "proofValue": "https://w3id.org/security#proofValue",
                "nonce": "https://w3id.org/security#nonce",
                "proofPurpose": {
                    "@id": "https://w3id.org/security#proofPurpose",
                    "@type": "@vocab",
                    "@context": {
                        "@version": 1.1,
                        "@protected": True,
                        "id": "@id",
                        "type": "@type",
                        "assertionMethod": {
                            "@id": "https://w3id.org/security#assertionMethod",
                            "@type": "@id",
                            "@container": "@set",
                        },
                        "authentication": {
                            "@id": "https://w3id.org/security#authenticationMethod",
                            "@type": "@id",
                            "@container": "@set",
                        },
                    },
                },
                "verificationMethod": {
                    "@id": "https://w3id.org/security#verificationMethod",
                    "@type": "@id",
                },
            },
        },
        "BbsBlsSignatureProof2020": {
            "@id": "https://w3id.org/security#BbsBlsSignatureProof2020",
            "@context": {
                "@version": 1.1,
                "@protected": True,
                "id": "@id",
                "type": "@type",
                "challenge": "https://w3id.org/security#challenge",
                "created": {
                    "@id": "http://purl.org/dc/terms/created",
                    "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
                },
                "domain": "https://w3id.org/security#domain",
                "nonce": "https://w3id.org/security#nonce",
                "proofPurpose": {
                    "@id": "https://w3id.org/security#proofPurpose",
                    "@type": "@vocab",
                    "@context": {
                        "@version": 1.1,
                        "@protected": True,
                        "id": "@id",
                        "type": "@type",
                        "sec": "https://w3id.org/security#",
                        "assertionMethod": {
                            "@id": "https://w3id.org/security#assertionMethod",
                            "@type": "@id",
                            "@container": "@set",
                        },
                        "authentication": {
                            "@id": "https://w3id.org/security#authenticationMethod",
                            "@type": "@id",
                            "@container": "@set",
                        },
                    },
                },
                "proofValue": "https://w3id.org/security#proofValue",
                "verificationMethod": {
                    "@id": "https://w3id.org/security#verificationMethod",
                    "@type": "@id",
                },
            },
        },
        "Bls12381G1Key2020": "https://w3id.org/security#Bls12381G1Key2020",
        "Bls12381G2Key2020": "https://w3id.org/security#Bls12381G2Key2020",
    }
}
