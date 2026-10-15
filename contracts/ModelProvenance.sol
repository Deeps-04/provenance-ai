// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ModelProvenance
 * @notice Immutable registry for ML model lineage and dataset attestation
 */
contract ModelProvenance {
    address public owner;

    enum ModelStatus { Active, Deprecated, Compromised }

    struct ModelRecord {
        string modelName;
        string version;
        bytes32 datasetMerkleRoot;
        bytes32 modelWeightsHash;
        address publisher;
        uint256 timestamp;
        ModelStatus status;
        bool exists;
    }

    mapping(bytes32 => ModelRecord) private models;
    bytes32[] public registeredModelIds;

    event ModelRegistered(
        bytes32 indexed modelId,
        string modelName,
        string version,
        bytes32 datasetMerkleRoot,
        bytes32 modelWeightsHash,
        address indexed publisher,
        uint256 timestamp
    );

    event ModelStatusChanged(bytes32 indexed modelId, ModelStatus status);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only registry authority can perform this action");
        _;
    }

    modifier onlyPublisher(bytes32 _modelId) {
        require(models[_modelId].exists, "Model not registered");
        require(models[_modelId].publisher == msg.sender || msg.sender == owner, "Not authorized");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function registerModel(
        string calldata _modelName,
        string calldata _version,
        bytes32 _datasetMerkleRoot,
        bytes32 _modelWeightsHash
    ) external returns (bytes32) {
        bytes32 modelId = keccak256(abi.encodePacked(_modelName, _version));
        require(!models[modelId].exists, "Model version already registered");

        models[modelId] = ModelRecord({
            modelName: _modelName,
            version: _version,
            datasetMerkleRoot: _datasetMerkleRoot,
            modelWeightsHash: _modelWeightsHash,
            publisher: msg.sender,
            timestamp: block.timestamp,
            status: ModelStatus.Active,
            exists: true
        });

        registeredModelIds.push(modelId);

        emit ModelRegistered(
            modelId,
            _modelName,
            _version,
            _datasetMerkleRoot,
            _modelWeightsHash,
            msg.sender,
            block.timestamp
        );

        return modelId;
    }

    function verifyModel(
        string calldata _modelName,
        string calldata _version,
        bytes32 _targetDatasetRoot,
        bytes32 _targetWeightsHash
    ) external view returns (bool isAuthentic, string memory message) {
        bytes32 modelId = keccak256(abi.encodePacked(_modelName, _version));
        
        if (!models[modelId].exists) {
            return (false, "Model ID not found on blockchain");
        }

        ModelRecord memory rec = models[modelId];

        if (rec.status == ModelStatus.Compromised) {
            return (false, "Security Alert: Model marked as COMPROMISED by publisher");
        }
        if (rec.status == ModelStatus.Deprecated) {
            return (false, "Warning: Model is DEPRECATED");
        }
        if (rec.datasetMerkleRoot != _targetDatasetRoot) {
            return (false, "Integrity Failure: Dataset Merkle Root mismatch (Data Poisoning detected)");
        }
        if (rec.modelWeightsHash != _targetWeightsHash) {
            return (false, "Integrity Failure: Model weights altered (Weights Tampering detected)");
        }

        return (true, "Cryptographic Proof Verified: Model & Dataset are authentic");
    }

    function updateStatus(bytes32 _modelId, ModelStatus _status) external onlyPublisher(_modelId) {
        models[_modelId].status = _status;
        emit ModelStatusChanged(_modelId, _status);
    }

    function getModel(bytes32 _modelId) external view returns (ModelRecord memory) {
        require(models[_modelId].exists, "Model does not exist");
        return models[_modelId];
    }
}
