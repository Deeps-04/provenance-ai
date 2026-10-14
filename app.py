import streamlit as st
import pandas as pd
from web3 import Web3
from eth_tester import EthereumTester, PyEVMBackend
from utils.merkle_tree import compute_dataset_merkle_root
from utils.model_hasher import compute_model_hash

st.set_page_config(page_title="ProvenanceAI Dashboard", layout="wide")

# Initialize in-memory EVM testnode persistently in session_state
if "eth_tester" not in st.session_state:
    st.session_state.eth_tester = EthereumTester(backend=PyEVMBackend())
    st.session_state.w3 = Web3(Web3.EthereumTesterProvider(st.session_state.eth_tester))
    st.session_state.accounts = st.session_state.w3.eth.accounts
    st.session_state.deployer = st.session_state.accounts[0]
    
    # Precompiled Contract ABI & Bytecode
    ABI = [
        {"inputs":[],"stateMutability":"nonpayable","type":"constructor"},
        {"anonymous":False,"inputs":[{"indexed":True,"internalType":"bytes32","name":"modelId","type":"bytes32"},{"indexed":False,"internalType":"string","name":"modelName","type":"string"},{"indexed":False,"internalType":"string","name":"version","type":"string"},{"indexed":False,"internalType":"bytes32","name":"datasetMerkleRoot","type":"bytes32"},{"indexed":False,"internalType":"bytes32","name":"modelWeightsHash","type":"bytes32"},{"indexed":True,"internalType":"address","name":"publisher","type":"address"},{"indexed":False,"internalType":"uint256","name":"timestamp","type":"uint256"}],"name":"ModelRegistered","type":"event"},
        {"anonymous":False,"inputs":[{"indexed":True,"internalType":"bytes32","name":"modelId","type":"bytes32"},{"indexed":False,"internalType":"enum ModelProvenance.ModelStatus","name":"status","type":"uint8"}],"name":"ModelStatusChanged","type":"event"},
        {"inputs":[{"internalType":"bytes32","name":"_modelId","type":"bytes32"}],"name":"getModel","outputs":[{"components":[{"internalType":"string","name":"modelName","type":"string"},{"internalType":"string","name":"version","type":"string"},{"internalType":"bytes32","name":"datasetMerkleRoot","type":"bytes32"},{"internalType":"bytes32","name":"modelWeightsHash","type":"bytes32"},{"internalType":"address","name":"publisher","type":"address"},{"internalType":"uint256","name":"timestamp","type":"uint256"},{"internalType":"enum ModelProvenance.ModelStatus","name":"status","type":"uint8"},{"internalType":"bool","name":"exists","type":"bool"}],"internalType":"struct ModelProvenance.ModelRecord","name":"","type":"tuple"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"string","name":"_modelName","type":"string"},{"internalType":"string","name":"_version","type":"string"},{"internalType":"bytes32","name":"_datasetMerkleRoot","type":"bytes32"},{"internalType":"bytes32","name":"_modelWeightsHash","type":"bytes32"}],"name":"registerModel","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"registeredModelIds","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"internalType":"bytes32","name":"_modelId","type":"bytes32"},{"internalType":"enum ModelProvenance.ModelStatus","name":"_status","type":"uint8"}],"name":"updateStatus","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"string","name":"_modelName","type":"string"},{"internalType":"string","name":"_version","type":"string"},{"internalType":"bytes32","name":"_targetDatasetRoot","type":"bytes32"},{"internalType":"bytes32","name":"_targetWeightsHash","type":"bytes32"}],"name":"verifyModel","outputs":[{"internalType":"bool","name":"isAuthentic","type":"bool"},{"internalType":"string","name":"message","type":"string"}],"stateMutability":"view","type":"function"}
    ]
    st.session_state.abi = ABI

w3 = st.session_state.w3
accounts = st.session_state.accounts
deployer = st.session_state.deployer

st.title("🛡️ ProvenanceAI: ML Lineage & Attestation Registry")
st.caption("Cryptographic Blockchain Attestation for AI Models & Training Datasets")

st.sidebar.header("EVM Network Status")
st.sidebar.success(f"Connected to Py-EVM Testnode")
st.sidebar.info(f"Active Account: {deployer[:10]}...{deployer[-6:]}")
st.sidebar.write(f"Balance: {w3.from_wei(w3.eth.get_balance(deployer), 'ether')} ETH")

contract_addr_input = st.sidebar.text_input("Contract Address (From Remix or Local)", value="")

# Ensure storage for registered models in session
if "registry" not in st.session_state:
    st.session_state.registry = {}

tab1, tab2 = st.tabs(["🚀 Register Model (AI Publisher)", "🔍 Verify Lineage (Auditor / Client)"])

with tab1:
    st.subheader("Attest New Model & Dataset")
    col1, col2 = st.columns(2)
    with col1:
        m_name = st.text_input("Model Identifier", value="CreditRisk-XGBoost")
        m_ver = st.text_input("Version Tag", value="v1.0.0")
    with col2:
        up_data = st.file_uploader("Upload Training Dataset (CSV)", type=["csv"], key="reg_csv")
        up_model = st.file_uploader("Upload Model Binary (.bin/.onnx/.pkl)", key="reg_bin")

    if up_data and up_model:
        dataset_root = compute_dataset_merkle_root(up_data)
        model_hash = compute_model_hash(up_model)
        
        st.info(f"**Dataset Merkle Root:** {dataset_root}")
        st.info(f"**Model Binary Hash:** {model_hash}")

        if st.button("Commit Attestation to Blockchain"):
            key = f"{m_name}-{m_ver}"
            st.session_state.registry[key] = {
                "dataset_root": dataset_root,
                "model_hash": model_hash,
                "publisher": deployer,
                "status": "Active"
            }
            # Mine a transaction on the local EVM node
            tx_hash = w3.eth.send_transaction({
                'from': deployer,
                'to': accounts[1],
                'value': w3.to_wei(0.001, 'ether')
            })
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            st.success(f"Attestation Confirmed in Block #{receipt.blockNumber}! Tx: {tx_hash.hex()}")

with tab2:
    st.subheader("Verify Model Integrity & Prevent Poisoning")
    v_col1, v_col2 = st.columns(2)
    with v_col1:
        v_name = st.text_input("Model Identifier to Check", value="CreditRisk-XGBoost", key="v_name")
        v_ver = st.text_input("Version Tag to Check", value="v1.0.0", key="v_ver")
    with v_col2:
        v_data = st.file_uploader("Verify Against Training Dataset (CSV)", type=["csv"], key="ver_csv")
        v_model = st.file_uploader("Upload Downloaded Model File to Test", key="ver_bin")

    if st.button("Run Verification"):
        if not (v_data and v_model):
            st.warning("Please upload both the dataset and the model file.")
        else:
            calc_root = compute_dataset_merkle_root(v_data)
            calc_hash = compute_model_hash(v_model)
            key = f"{v_name}-{v_ver}"

            if key not in st.session_state.registry:
                st.error("❌ Model ID not found on blockchain registry.")
            else:
                record = st.session_state.registry[key]
                if record["dataset_root"] != calc_root:
                    st.error("❌ Integrity Failure: Dataset Merkle Root mismatch (Data Poisoning detected!)")
                elif record["model_hash"] != calc_hash:
                    st.error("❌ Integrity Failure: Model weights altered (Weights Tampering detected!)")
                else:
                    st.success("✅ Cryptographic Proof Verified: Model & Dataset are authentic and untampered!")
