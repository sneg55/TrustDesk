// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IValidationRegistry} from "./interfaces/IValidationRegistry.sol";

/// @title TrustDeskOpenValidator
/// @notice Permissionless wrapper around the ERC-8004 Validation Registry.
///         Anyone with a Base Sepolia wallet can post a validation opinion on
///         any TrustDesk trade proposal.
contract TrustDeskOpenValidator {
    // ---------------------------------------------------------------
    //  Storage
    // ---------------------------------------------------------------

    IValidationRegistry public immutable registry;

    struct ExternalValidation {
        address validator;
        uint256 agentId;
        bytes32 requestHash;
        bool approved;
        string reason;
        string evidenceURI;
        uint256 timestamp;
    }

    /// requestHash => list of external validations
    mapping(bytes32 => ExternalValidation[]) public validationsByRequest;

    /// Total validations ever submitted (useful for dashboard stats)
    uint256 public totalValidations;

    // ---------------------------------------------------------------
    //  Events
    // ---------------------------------------------------------------

    /// @notice Emitted every time someone submits an external validation.
    event TradeValidated(
        address indexed validator,
        uint256 indexed agentId,
        bytes32 indexed requestHash,
        bool approved,
        string reason,
        string evidenceURI
    );

    // ---------------------------------------------------------------
    //  Errors
    // ---------------------------------------------------------------

    error ZeroRequestHash();
    error EmptyReason();

    // ---------------------------------------------------------------
    //  Constructor
    // ---------------------------------------------------------------

    /// @param _registry Address of the deployed ERC-8004 ValidationRegistry.
    constructor(address _registry) {
        registry = IValidationRegistry(_registry);
    }

    // ---------------------------------------------------------------
    //  Core
    // ---------------------------------------------------------------

    /// @notice Submit an external validation for a TrustDesk trade.
    /// @param agentId      The TrustDesk agent whose trade you are validating.
    /// @param requestHash  Keccak-256 of the original trade proposal.
    /// @param approved     Your opinion — approve or reject.
    /// @param reason       Human-readable explanation.
    /// @param evidenceURI  Optional URI to supporting evidence (IPFS, https, etc.).
    function validateTrade(
        uint256 agentId,
        bytes32 requestHash,
        bool approved,
        string calldata reason,
        string calldata evidenceURI
    ) external {
        if (requestHash == bytes32(0)) revert ZeroRequestHash();
        if (bytes(reason).length == 0) revert EmptyReason();

        // Store for on-chain query
        validationsByRequest[requestHash].push(
            ExternalValidation({
                validator: msg.sender,
                agentId: agentId,
                requestHash: requestHash,
                approved: approved,
                reason: reason,
                evidenceURI: evidenceURI,
                timestamp: block.timestamp
            })
        );

        unchecked {
            ++totalValidations;
        }

        // Forward to the ERC-8004 Validation Registry
        bytes32 responseHash = keccak256(abi.encodePacked(approved, reason));
        registry.validationResponse(
            requestHash,
            approved,
            evidenceURI,
            responseHash,
            "trade,external,trustdesk"
        );

        emit TradeValidated(
            msg.sender,
            agentId,
            requestHash,
            approved,
            reason,
            evidenceURI
        );
    }

    // ---------------------------------------------------------------
    //  Views
    // ---------------------------------------------------------------

    /// @notice How many external validations exist for a given request.
    function validationCount(bytes32 requestHash) external view returns (uint256) {
        return validationsByRequest[requestHash].length;
    }

    /// @notice Retrieve a single validation by request hash and index.
    function getValidation(
        bytes32 requestHash,
        uint256 index
    ) external view returns (ExternalValidation memory) {
        return validationsByRequest[requestHash][index];
    }
}
