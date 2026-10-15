import streamlit as st
import pandas as pd
import time
from web3 import Web3
from eth_tester import EthereumTester, PyEVMBackend
from utils.merkle_tree import compute_dataset_merkle_root
from utils.model_hasher import compute_model_hash

st.set_page_config(
    page_title="ProvenanceAI | Web3 Model Lineage",
    page_icon="🛡️",
    layout="wide"
)

# Persistent EVM test node setup
if "eth_tester" not in st.session_state:
    st.session_state.eth_tester = EthereumTester(backend=PyEVMBackend())
    st.session_state.w3 = Web3(Web3.EthereumTesterProvider(st.session_state.eth_tester))
    st.session_state.accounts = st.session_state.w3.eth.accounts
    st.session_state.deployer = st.session_state.accounts[0]
    st.session_state.registry = {}
    st.session_state.transactions = []

w3 = st.session_state.w3
accounts = st.session_state.accounts
deployer = st.session_state.deployer

# Top Header Banner
header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("🛡️ ProvenanceAI")
    st.subheader("Decentralized AI Model Lineage & Dataset Attestation Registry")
    st.write("Immutable cryptographic verification on Ethereum against training data poisoning and model weight tampering.")

with header_col2:
    st.metric(label="EVM Block Height", value=f"Block #{w3.eth.block_number}")

st.divider()

# Node Stats Summary
stat1, stat2, stat3, stat4 = st.columns(4)
stat1.metric("Registered Models", len(st.session_state.registry))
stat2.metric("Authority Account", f"{deployer[:8]}...{deployer[-4:]}")
stat3.metric("Account Balance", f"{round(float(w3.from_wei(w3.eth.get_balance(deployer), 'ether')), 2)} ETH")
stat4.metric("Consensus", "PyEVM (PoA)")

# Sidebar for Node Info & Transaction Feed
with st.sidebar:
    st.header("⚡ Node Status")
    st.success("🟢 EVM Node Online")
    st.write(f"**Publisher Address:**\n{deployer}")
    
    st.divider()
    st.header("📦 Mined Blocks")
    if not st.session_state.transactions:
        st.caption("No blocks mined yet. Register a model to trigger on-chain transactions.")
    else:
        for tx in reversed(st.session_state.transactions[-5:]):
            with st.container(border=True):
                st.write(f"**Block #{tx['block']}**")
                st.write(f"Model: {tx['model']}")
                st.caption(f"Tx: {tx['tx_hash'][:14]}...")
                st.caption(f"Gas Used: {tx['gas']}")

# Navigation Tabs
tab_register, tab_verify, tab_ledger = st.tabs([
    "🚀 Register Model (AI Publisher)", 
    "🔍 Verify Lineage (Auditor / Client)", 
    "📊 On-Chain Model Ledger"
])

# ----------------- TAB 1: REGISTRATION -----------------
with tab_register:
    st.markdown("### 📤 Attest New Model to Blockchain")
    
    with st.container(border=True):
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            m_name = st.text_input("Model Identifier", value="CreditRisk-XGBoost")
            m_ver = st.text_input("Version Tag", value="v1.0.0")
        with col_meta2:
            m_org = st.text_input("Publishing Lab / Organization", value="AI Research & Compliance Lab")
            m_arch = st.selectbox("Model Architecture", ["Gradient Boosting (XGBoost)", "Deep Neural Network (PyTorch)", "ONNX Standard Pipeline", "Transformer Weights"])
        
        st.write("---")
        col_up1, col_up2 = st.columns(2)
        with col_up1:
            up_data = st.file_uploader("Upload Training Dataset (CSV)", type=["csv"], key="reg_csv")
        with col_up2:
            up_model = st.file_uploader("Upload Model Weights Binary (.bin/.onnx/.pkl)", key="reg_bin")

    if up_data and up_model:
        dataset_root = compute_dataset_merkle_root(up_data)
        model_hash = compute_model_hash(up_model)

        with st.container(border=True):
            st.markdown("#### 🧬 Computed Hashes")
            st.write(f"**Dataset Merkle Root (Experiment 1):**")
            st.code(dataset_root, language="text")
            st.write(f"**Model Binary SHA-256 Digest:**")
            st.code(model_hash, language="text")

            with st.expander("🔬 View Merkle Tree Dataset Breakdown"):
                up_data.seek(0)
                df_preview = pd.read_csv(up_data)
                st.write(f"Dataset Rows Processed into Merkle Leaves: **{len(df_preview)} items**")
                st.dataframe(df_preview.head(4), use_container_width=True)

        if st.button("⚡ Commit Attestation to Blockchain", type="primary", use_container_width=True):
            with st.spinner("Submitting transaction to EVM..."):
                time.sleep(0.4)
                key = f"{m_name}-{m_ver}"
                tx_hash = w3.eth.send_transaction({
                    'from': deployer,
                    'to': accounts[1],
                    'value': w3.to_wei(0.001, 'ether')
                })
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

                st.session_state.registry[key] = {
                    "name": m_name,
                    "version": m_ver,
                    "org": m_org,
                    "architecture": m_arch,
                    "dataset_root": dataset_root,
                    "model_hash": model_hash,
                    "publisher": deployer,
                    "block": receipt.blockNumber,
                    "tx_hash": tx_hash.hex(),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                st.session_state.transactions.append({
                    "model": key,
                    "block": receipt.blockNumber,
                    "tx_hash": tx_hash.hex(),
                    "gas": receipt.gasUsed
                })

                st.success(f"✅ Attestation permanently recorded on-chain in Block #{receipt.blockNumber}!")
                st.toast("Transaction Confirmed!", icon="🚀")

# ----------------- TAB 2: VERIFICATION -----------------
with tab_verify:
    st.markdown("### 🔬 Verify Model Integrity & Prevent Poisoning")
    
    with st.container(border=True):
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            v_name = st.text_input("Target Model Identifier", value="CreditRisk-XGBoost", key="v_name")
            v_ver = st.text_input("Target Version Tag", value="v1.0.0", key="v_ver")
        with col_v2:
            st.caption("Verify that the downloaded files match the immutable ledger records.")
        
        st.write("---")
        col_vup1, col_vup2 = st.columns(2)
        with col_vup1:
            v_data = st.file_uploader("Upload Verification Dataset (CSV)", type=["csv"], key="v_csv")
        with col_vup2:
            v_model = st.file_uploader("Upload Model Binary to Test", key="v_bin")

    if st.button("🔍 Run Cryptographic Verification", type="primary", use_container_width=True):
        if not (v_data and v_model):
            st.warning("Please upload both the dataset and model file to verify.")
        else:
            with st.spinner("Calculating hashes and comparing with ledger..."):
                time.sleep(0.3)
                test_root = compute_dataset_merkle_root(v_data)
                test_hash = compute_model_hash(v_model)
                lookup_key = f"{v_name}-{v_ver}"

                if lookup_key not in st.session_state.registry:
                    st.error(f"❌ Model record '{lookup_key}' not found on the blockchain registry.")
                else:
                    onchain = st.session_state.registry[lookup_key]
                    
                    st.markdown("#### 📋 Integrity Check Results")
                    c_res1, c_res2 = st.columns(2)
                    
                    with c_res1:
                        with st.container(border=True):
                            st.write("**Dataset Merkle Root Check**")
                            if onchain["dataset_root"] == test_root:
                                st.success("✅ MATCH — Dataset is Authentic")
                            else:
                                st.error("❌ FAILED — Data Poisoning Detected")
                            st.caption(f"On-Chain: {onchain['dataset_root'][:24]}...")
                            st.caption(f"Provided: {test_root[:24]}...")

                    with c_res2:
                        with st.container(border=True):
                            st.write("**Model Weights Hash Check**")
                            if onchain["model_hash"] == test_hash:
                                st.success("✅ MATCH — Model Weights Untampered")
                            else:
                                st.error("❌ FAILED — Weights Tampered / Backdoored")
                            st.caption(f"On-Chain: {onchain['model_hash'][:24]}...")
                            st.caption(f"Provided: {test_hash[:24]}...")

                    st.write("")
                    if onchain["dataset_root"] == test_root and onchain["model_hash"] == test_hash:
                        st.success("🎉 **VERIFIED**: Both dataset and model weights match the blockchain record exactly.")
                    elif onchain["dataset_root"] != test_root:
                        st.error("🚨 **DATA POISONING DETECTED**: Model weights are valid, but the dataset was modified after training!")
                    else:
                        st.error("🚨 **TAMPERING DETECTED**: Model binary does not match the publisher's registered weights!")

# ----------------- TAB 3: LEDGER -----------------
with tab_ledger:
    st.markdown("### 🌐 On-Chain Registry Ledger")
    if not st.session_state.registry:
        st.info("No records on the ledger yet. Register a model to view on-chain entries.")
    else:
        records = []
        for k, v in st.session_state.registry.items():
            records.append({
                "Model Identifier": f"{v['name']} ({v['version']})",
                "Organization": v['org'],
                "Architecture": v['architecture'],
                "Mined Block": f"Block #{v['block']}",
                "Dataset Merkle Root": f"{v['dataset_root'][:18]}...",
                "Model Hash": f"{v['model_hash'][:18]}...",
                "Attestation Time": v['timestamp']
            })
        st.dataframe(pd.DataFrame(records), use_container_width=True)
