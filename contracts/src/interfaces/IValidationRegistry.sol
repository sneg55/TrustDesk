// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IValidationRegistry
/// @notice ERC-8004 Validation Registry interface — the subset TrustDesk needs.
interface IValidationRegistry {
    /// @notice Submit a validation response for a previously created request.
    /// @param requestHash  The hash identifying the validation request.
    /// @param approved     Whether the validator approves.
    /// @param responseURI  URI pointing to the full response payload (e.g. IPFS).
    /// @param responseHash Keccak-256 of the response payload for integrity.
    /// @param tags         Comma-separated tags for indexing ("trade,risk,external").
    function validationResponse(
        bytes32 requestHash,
        bool approved,
        string calldata responseURI,
        bytes32 responseHash,
        string calldata tags
    ) external;
}
