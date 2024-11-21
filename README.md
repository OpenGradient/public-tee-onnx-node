# TEE Inference Node
This project creates an application that dynamically downloads models over IPFS and runs ONNX models within a Trusted Execution Environment (TEE). This runs on Amazon's nitro-enclave, and uses Nitriding to provide secure networking using HTTPS.

## Setup
[Link](https://docs.google.com/document/d/1BOmWU5njSl-R9BuBOEhJA878tljPZ24zQanLydxLiso/edit)
To share the document, contact me: kyle@opengradient.ai

Basically, set up an EC2 instance that has nitro-enclave capability. Download all the appropriate tools to enable nitro enclaves (mainly docker), the nitro-cli itself, and increase the nitro-cli memory allocation (optional).

After this, download Go, golangci-lint, and gvproxy. These are needed for nitriding.

The commands to do all of this are in the linked document.

## Run
To run the service simply call `make`

## Usage
Currently all requests are being made insecurely as we haven't set up the TLS Certification.

Requests to this service are done through the OpenGradient inference nodes. You can manually make inference requests to these TEEs by sending a POST request to the endpoint `https://<ec2-ip>:8000/infer` with the JSON structure:
```
{
  "ipfs_hash": modelHash,
  "num_inputs": num_inputs,
  "string_inputs": string_inputs
}
```
where `num_inputs` and `string_inputs` are both lists of the model inputs with all entries converted to string types.

## Remote Attestation
Using nitriding we support the public HTTP API endpoints that they provide [More on that here](https://github.com/brave/nitriding-daemon/blob/master/doc/http-api.md)

To generate remote attestations
`curl -k -G "https://<ec2-ip>/enclave/attestation" --data-urlencode "nonce=<nonce>`

Check elsewhere for scripts to verify the remote attestation.
