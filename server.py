#!/usr/bin/env python3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import onnxruntime as ort
import urllib.request
import numpy as np
import time
from storage import storage
import utils
import requests

### Nitriding testing ###
nitriding_url = "http://127.0.0.1:8080/enclave/ready"

def signal_ready():
    r = urllib.request.urlopen(nitriding_url)
    if r.getcode() != 200:
        raise Exception("Expected status code %d but got %d" %
                        (requests.status_codes.codes.ok, r.status_code))

app = FastAPI()

# Inititalize Storage Manager
storage = storage.StorageManager()

class InferenceRequest(BaseModel):
    ipfs_hash: str
    model_inputs: str

class InferenceResponse(BaseModel):
    output: list
    model_hash: str

@app.post("/infer")
async def infer(request: InferenceRequest):
    # Get model from storage
    model_path = storage.get(request.ipfs_hash)

    # Create ONNX session
    session = ort.InferenceSession(model_path)

    # Convert API inputs into ONNX inputs
    input_names = session.get_inputs()
    print("Model inputs: ", request.model_inputs)

    onnx_inputs = utils.convert_to_onnx_input(input_names, request.model_inputs)
    print("Onnx inputs: ", onnx_inputs)

    # Run inference
    onnx_outputs = [output.name for output in session.get_outputs()]
    print("Onnx outputs: ", onnx_outputs)
    result = session.run(onnx_outputs, onnx_inputs)
    print("Inference Result: ", result)

    # Serialize ONNX results for return JSON
    infer_output = utils.serialize_onnx_output(session_outputs=session.get_outputs(), results=result)
    print("Inference results: ", infer_output)

    # TODO (Kyle): Model hash should go into the attestation document that is returned as part of
    #              any inference -- Along with model input, and model output.
    # Get hash of model as checksum
    model_hash = utils.hash_model(model_path)

    return InferenceResponse(output=infer_output, 
                             model_hash=model_hash)
    
# Main entry point to start the server
if __name__ == "__main__":
    print("[py] Starting enclave server...")

    # Signal to nitriding that the enclave has finished bootstrapping and is ready.
    signal_ready()
    print("[py] Signalled to nitriding that we're ready.")

    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
