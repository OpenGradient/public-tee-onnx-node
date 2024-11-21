import hashlib
import numpy as np
import json
from typing import Union
from decimal import Decimal

"""
Hash the ONNX model to serve as checksum 
"""
def hash_model(filename: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

### Copied from inference node ###
# Constant decimal precision limit for 64-bit system
DECIMAL_LIMIT = 18

"""
Converts to float / int type based on ONNX model session inputs. Add more types as needed.
"""
def convert_to_float(fixed_point_num: dict, input_type) -> Union[np.integer, np.float32, np.float64]:
    # Check limit for decimal based on float64 precision 
    if int(fixed_point_num["decimals"]) > DECIMAL_LIMIT:
        raise ValueError("Decimal value greater than precision limit: %s" % fixed_point_num["decimals"])

    if input_type == 'tensor(float)':
        number = _convert_to_float32(fixed_point_num)
    elif input_type in ['tensor(double)', 'tensor(float64)']:
        number = _convert_to_float64(fixed_point_num)
    elif input_type.startswith('tensor(int') or input_type.startswith('tensor(uint'):
        number = _convert_to_int(fixed_point_num)
    else:
        raise TypeError("Unsupported input type: %s " % input_type)

    return number

"""
Converts a fixed-point number to float64
"""
def _convert_to_float64(fixed_point_num: dict) -> np.float64:
    print("Convert to float64 value: ", fixed_point_num["value"])
    print("Convert to float64 decimal: ", fixed_point_num["decimals"])
    return np.float64(Decimal(fixed_point_num["value"]) / Decimal(10 ** int(fixed_point_num["decimals"])))

"""
Converts a fixed-point number to float32
"""
def _convert_to_float32(fixed_point_num: dict) -> np.float32:
    print("Convert to float32 value: ", fixed_point_num["value"])
    print("Convert to float32 decimal: ", fixed_point_num["decimals"])
    return np.float32(Decimal(fixed_point_num["value"]) / Decimal(10 ** int(fixed_point_num["decimals"])))

"""
Converts to fixed-point number to an int
"""
def _convert_to_int(fixed_point_num: dict) -> np.integer:
    print("Convert to int value: ", fixed_point_num["value"])
    print("Convert to int decimal: ", fixed_point_num["decimals"])
    return np.int_(Decimal(fixed_point_num["value"]) / Decimal(10 ** int(fixed_point_num["decimals"])))

supported_input_types_num = {
    'tensor(float)',
    'tensor(float64)',
    'tensor(double)',
}

supported_input_types_string = {
    'tensor(string)'
}

"""
Converts number and string input lists into dictionary usable as ONNX input
"""
def convert_to_onnx_input(session_inputs: list, model_input: str) -> dict:
    inputs = {}

    # Convert model input into JSON dict
    model_input_dict = json.loads(model_input)
    print("JSON inputs: ", model_input_dict)

    # Convert number inputs to dict based on name
    num_inputs = {}
    if "numbers" in model_input_dict:
        num_inputs = {
            number_tensor["name"]: number_tensor
            for number_tensor in model_input_dict["numbers"]
        }
    print("Num inputs: ", num_inputs)

    # Convert string inputs to dict based on name
    string_inputs = {}
    if "strings" in model_input_dict:
        string_inputs = {
            string_input["name"]: string_input
            for string_input in model_input_dict["strings"]
        }
    print("string inputs: ", string_inputs)

    inputs = {}
    for session_input in session_inputs:
        print("Session Input: ", session_input)
        
        if session_input.name in num_inputs:
            # Check if we support this input type for number tensor
            if session_input.type not in supported_input_types_num and not session_input.type.startswith('tensor(int') and not not session_input.type.startswith('tensor(uint'):
                print("Unexpected input type provided: ", session_input.type)

            num_input = num_inputs[session_input.name]
            flattened_input = np.array([convert_to_float(num, session_input.type) for num in num_input["values"]])
            input_tensor = flattened_input.reshape(num_input["shape"])

        elif session_input.name in string_inputs:
            # Check if we support this input type for string tensor
            if session_input.type not in supported_input_types_string:
                print("Unexpected input type provided: ", session_input.type)

            str_input = string_inputs[session_input.name]
            flattened_input = np.array(str_input["values"])
            input_tensor = flattened_input.reshape(str_input["shape"])

        else:
            raise RuntimeError("Input not found: %s" % session_input.name)
        
        print("Input Tensor: ", input_tensor)
        inputs[session_input.name] = input_tensor

    print("Model input: ", inputs)
    return inputs

"""
Converts from ONNX output into a list of dicts of inference result, data type, and output name
"""
def serialize_onnx_output(session_outputs: list, results: list) -> list:
    output = []

    for i, session_output in enumerate(session_outputs):
        print("Processing session output: ", session_output)
        output_dict = {}
        result = results[i]

        # If result is not numpy array, convert to numpy array
        if not isinstance(result, np.ndarray):
            try:
                result = np.array(results[i])
            except Exception as e:
                raise RuntimeError("Failed to convert output to numpy array: %s" % e)
            
        # Prepare output dictionary 
        output_dict["name"] = session_output.name
        output_dict["shape"] = result.shape  # Use result shape
        output_dict["result"]= result.tolist()      
            
        # Type is simply whether or not it's a number or string tensor. Inference node will
        # convert to fixed point afterwards.
        if issubclass(result.dtype.type, np.floating) or issubclass(result.dtype.type, np.integer):
            output_dict["type"] = "number"
        elif result.dtype == np.object_ and isinstance(result.flatten()[0], str):
            output_dict["type"] = "string"
        else:
            raise RuntimeError("Output type not found: %s" % session_output.type)
        
        print("Adding output dict: ", output_dict)
        output.append(output_dict)
    
    print("Returning inference output: ", output_dict)
    return output
    
