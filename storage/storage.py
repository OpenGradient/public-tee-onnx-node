from collections import OrderedDict, namedtuple
import os
# import diskcache
import subprocess

ModelEntry = namedtuple("ModelEntry", ["path", "size"])

class StorageManager():
    def __init__(self):
        """
        Simple single-threade LRU Storage system

        Cache is an ordered dict:
            key: model_hash
            value: (model_path, model_size)
        """
        self.model_dir = "./storage/models"
        self.capacity = 40e9   # 40 GB
        self.current_size = 0
        self.cache = OrderedDict()

        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)

    def get(self, modelHash: str):
        """
        Gets model hash path if in cache. If not, then download the model and return its path.
        """
        if modelHash in self.cache:
            # Move accessed item to most recently used
            self.cache.move_to_end(modelHash)

            model = self.cache[modelHash]
            if not os.path.exists(model.path):
                self._downloadModel(modelHash)

            print(f"Model hash {modelHash} found in cache, returning path {model.path}")
            return model.path
        
        # Check IPFs if model fits within cache
        size = self._getModelSize(modelHash)
        if size > self.capacity:
            raise ValueError("Model size for %s greater than max capacity", modelHash)
        
        # Evict cache based on LRU policy until we have room to download new model
        while size + self.current_size > self.capacity:
            model = self.cache.popitem(last=False).size
            os.remove(model.path)
            self.current_size -= model.size
            print(f"Triggered cache eviction policy, removed file {model.path} of size {model.size}")

        # Download item from IPFS directly into OrderedDict
        path = self._downloadModel(modelHash)
        new_entry = ModelEntry(path, size)

        # Insert into cache
        self.cache[modelHash] = new_entry
        self.cache.move_to_end(modelHash)
        return new_entry.path

    
    def _downloadModel(self, modelHash):
        """
        Download and save the model data from IPFS. Returns the path to the saved data. 
        """
        # Check if file already exists
        output_path = os.path.join(self.model_dir, modelHash)
        if os.path.exists(output_path):
            print("Model already exists, returning path ", output_path)
            return output_path

        # Download model from IPFS
        # TODO (Kyle): Look into making this a streaming option
        command = ["ipfs", "get", "--output", output_path, modelHash]

        try:
            subprocess.run(command, check=True)
            print(f"Model {modelHash} downloaded successfully.")
        except subprocess.CalledProcessError as e:
            # If there's any error, make sure to remove the model hash from the cache
            print(f"Removed model hash {modelHash} from cache, failed to download from IPFS")
            raise RuntimeError(f"Failed to download model {modelHash} from IPFS")
        
        return output_path
    
    def _getModelSize(self, modelHash):
        """
        Get IPFS model size
        """
        command = ["ipfs", "files", "stat", "--size", f"/ipfs/{modelHash}"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())