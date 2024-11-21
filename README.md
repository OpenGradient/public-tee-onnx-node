# OpenGradient ONNX Inference Data Node
This project creates an application within a Trusted Execution Environment (TEE) that serves OpenGradient user requests to dynamically download models over IPFS and run inference using onnxruntime.

We utilize Amazon's [nitro-enclave](https://aws.amazon.com/ec2/nitro/nitro-enclaves/) for its TEE and remote attestation capabilities, along with [Nitriding](https://arxiv.org/pdf/2206.04123) to provide secure networking and data acquisition from the enclave over HTTPS.

## Node Setup
[Guide for setting up AWS nitro-enclave](https://docs.aws.amazon.com/enclaves/latest/user/create-enclave.html)

[Guide for using nitriding](https://github.com/brave/nitriding-daemon)

As a basic summary:
1. Set up an EC2 instance that has nitro-enclave capability -- found in the advanced settings
2. Download all the appropriate tools to enable nitro enclaves -- namely docker and the nitro-cli
3. (Optional) Increase the nitro-cli memory allocation
4. Download approparite tools to enable nitriding -- namely go, golangci-clint, and gvproxy

Follow the guides above for more in-depth details.

Once the node is set up, from the nitro-enclave parent instance run `nitro-cli describe-enclaves` in order to obtain the PCR measurements for your enclave. 

Confirm that your measurements match that of OpenGradient's [official PCR registry](https://docs.opengradient.ai/learn/architecture/data_nodes) in order to ensure that your data-node, and the nodes used by OpenGradient, are authentic.

## Run Application
To run the service simply call `make`

## Usage
In the future, an OpenGradient TLS certification will be required for all network requests. For the current testnet, all requests are being made insecurely.

Requests to this service are done through the OpenGradient's inference nodes on behalf of the OpenGradient blockchain. You can manually make inference requests to these TEEs by sending a POST request to the endpoint `https://<ec2-ip>:8000/infer` with the JSON structure:
```
{
  "ipfs_hash": modelHash,
  "num_inputs": num_inputs,
  "string_inputs": string_inputs
}
```
where `num_inputs` and `string_inputs` are both lists of the model inputs with all entries converted to string types.

## Remote Attestation
Using nitriding we support the public HTTP API endpoints that they provide. [More information for this API can be found here.](https://github.com/brave/nitriding-daemon/blob/master/doc/http-api.md)

To generate a remote attestation for your node you can run the command

```curl -k -G "https://<ec2-ip>/enclave/attestation" --data-urlencode "nonce=<nonce>```

These remote attestations are automatically checked for validity and correctness within the OpenGradient sequencer. This means that any result returned by the OpenGradient blockchain for a TEE inference request will already be verified as authentic and unmodified.

Also included in this project is a script `verify_attestation.py` if you would like to verify the attestation document on your own. The current expected PCR hashes can be found under `measurements.txt`.
