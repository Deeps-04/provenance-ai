import hashlib
import pandas as pd

def sha256_hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def compute_dataset_merkle_root(file_path_or_buffer) -> str:
    df = pd.read_csv(file_path_or_buffer)
    leaves = []
    
    for _, row in df.iterrows():
        row_str = ",".join(str(val) for val in row.values)
        leaves.append(sha256_hash(row_str.encode('utf-8')))

    if not leaves:
        return "0x" + "00" * 32

    current_level = leaves
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            combined = sha256_hash(left + right)
            next_level.append(combined)
        current_level = next_level

    return "0x" + current_level[0].hex()
