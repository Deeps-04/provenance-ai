import hashlib
import pandas as pd
from web3 import Web3
from eth_tester import EthereumTester, PyEVMBackend
from solcx import compile_standard, install_solc

print("1. Initializing Local Python EVM Blockchain...")
eth_tester = EthereumTester(backend=PyEVMBackend())
w3 = Web3(Web3.EthereumTesterProvider(eth_tester))

accounts = w3.eth.accounts
deployer = accounts[0]
print(f"Connected to in-memory EVM. Deployer account: {deployer}")

# Helper functions
def sha256_hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def compute_dataset_merkle_root(csv_path: str) -> bytes:
    df = pd.read_csv(csv_path)
    leaves = [sha256_hash(",".join(str(val) for val in row.values).encode('utf-8')) for _, row in df.iterrows()]
    current_level = leaves
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else left
            next_level.append(sha256_hash(left + right))
        current_level = next_level
    return current_level[0]

def compute_model_hash(model_path: str) -> bytes:
    with open(model_path, 'rb') as f:
        return hashlib.sha256(f.read()).digest()

print("\n2. Computing Digital Fingerprints for Artifacts...")
dataset_root = compute_dataset_merkle_root('sample_artifacts/sample_data.csv')
model_hash = compute_model_hash('sample_artifacts/dummy_model.bin')
print(f"Dataset Merkle Root: 0x{dataset_root.hex()}")
print(f"Model Weights Hash:  0x{model_hash.hex()}")

print("\n3. Compiling ModelProvenance.sol...")
install_solc("0.8.20")
with open("contracts/ModelProvenance.sol", "r") as f:
    solidity_code = f.read()

compiled_sol = compile_standard({
    "language": "Solidity",
    "sources": {"ModelProvenance.sol": {"content": solidity_code}},
    "settings": {"outputSelection": {"*": {"*": ["abi", "metadata", "evm.bytecode"]}}}
}, solc_version="0.8.20")

abi = compiled_sol['contracts']['ModelProvenance.sol']['ModelProvenance']['abi']
bytecode = compiled_sol['contracts']['ModelProvenance.sol']['ModelProvenance']['evm']['bytecode']['object']

print("4. Deploying Smart Contract to Local EVM...")
Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
tx_hash = Contract.constructor().transact({'from': deployer})
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
contract = w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)
print(f"Contract deployed at address: {tx_receipt.contractAddress}")

print("\n5. Registering Model on Blockchain...")
reg_tx = contract.functions.registerModel(
    "CreditRisk-XGBoost",
    "v1.0.0",
    dataset_root,
    model_hash
).transact({'from': deployer})
w3.eth.wait_for_transaction_receipt(reg_tx)
print("Model registered successfully!")

print("\n6. Running Verifications:")
# Test 1: Authentic Verification
is_valid, msg = contract.functions.verifyModel(
    "CreditRisk-XGBoost", "v1.0.0", dataset_root, model_hash
).call()
print(f"  [Authentic Test]  Valid: {is_valid} | Result: {msg}")

# Test 2: Tampered Weights Test (Simulating Backdoor)
tampered_hash = sha256_hash(b"BACKDOORED_WEIGHTS")
is_valid, msg = contract.functions.verifyModel(
    "CreditRisk-XGBoost", "v1.0.0", dataset_root, tampered_hash
).call()
print(f"  [Tampered Model]  Valid: {is_valid} | Result: {msg}")

# Test 3: Data Poisoning Test
tampered_dataset_root = sha256_hash(b"POISONED_CSV_ROW")
is_valid, msg = contract.functions.verifyModel(
    "CreditRisk-XGBoost", "v1.0.0", tampered_dataset_root, model_hash
).call()
print(f"  [Poisoned Data]   Valid: {is_valid} | Result: {msg}")
