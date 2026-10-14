import hashlib

def compute_model_hash(file_bytes_or_buffer) -> str:
    hasher = hashlib.sha256()
    
    if hasattr(file_bytes_or_buffer, 'read'):
        file_bytes_or_buffer.seek(0)
        while chunk := file_bytes_or_buffer.read(65536):
            hasher.update(chunk)
    else:
        hasher.update(file_bytes_or_buffer)
        
    return "0x" + hasher.hexdigest()
