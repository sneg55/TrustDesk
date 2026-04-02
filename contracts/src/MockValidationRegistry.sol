// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IValidationRegistry} from "./interfaces/IValidationRegistry.sol";

/// @title MockValidationRegistry
/// @notice Minimal ERC-8004 Validation Registry for Base Sepolia testing.
///         Records validation responses and emits events. No access control.
contract MockValidationRegistry is IValidationRegistry {
    event ValidationResponseRecorded(
        bytes32 indexed requestHash,
        address indexed validator,
        bool approved,
        string responseURI,
        string tags
    );

    struct Response {
        address validator;
        bool approved;
        string responseURI;
        bytes32 responseHash;
        string tags;
        uint256 timestamp;
    }

    mapping(bytes32 => Response[]) public responses;
    uint256 public totalResponses;

    function validationResponse(
        bytes32 requestHash,
        bool approved,
        string calldata responseURI,
        bytes32 responseHash,
        string calldata tags
    ) external {
        responses[requestHash].push(Response({
            validator: msg.sender,
            approved: approved,
            responseURI: responseURI,
            responseHash: responseHash,
            tags: tags,
            timestamp: block.timestamp
        }));
        totalResponses++;

        emit ValidationResponseRecorded(requestHash, msg.sender, approved, responseURI, tags);
    }

    function getResponseCount(bytes32 requestHash) external view returns (uint256) {
        return responses[requestHash].length;
    }
}
