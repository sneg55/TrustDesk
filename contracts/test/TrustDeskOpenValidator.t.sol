// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test, console2} from "forge-std/Test.sol";
import {TrustDeskOpenValidator} from "../src/TrustDeskOpenValidator.sol";
import {IValidationRegistry} from "../src/interfaces/IValidationRegistry.sol";

/// @dev Minimal mock that records calls so tests can assert against them.
contract MockValidationRegistry is IValidationRegistry {
    struct Call {
        bytes32 requestHash;
        bool approved;
        string responseURI;
        bytes32 responseHash;
        string tags;
    }

    Call[] public calls;

    function validationResponse(
        bytes32 requestHash,
        bool approved,
        string calldata responseURI,
        bytes32 responseHash,
        string calldata tags
    ) external override {
        calls.push(Call(requestHash, approved, responseURI, responseHash, tags));
    }

    function callCount() external view returns (uint256) {
        return calls.length;
    }
}

contract TrustDeskOpenValidatorTest is Test {
    TrustDeskOpenValidator public validator;
    MockValidationRegistry public mockRegistry;

    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");

    bytes32 public constant REQUEST_HASH = keccak256("trade-proposal-1");
    uint256 public constant AGENT_ID = 42;

    function setUp() public {
        mockRegistry = new MockValidationRegistry();
        validator = new TrustDeskOpenValidator(address(mockRegistry));
    }

    // ---- Happy path ----

    function test_validateTrade_storesValidation() public {
        vm.prank(alice);
        validator.validateTrade(
            AGENT_ID,
            REQUEST_HASH,
            true,
            "Looks good, risk is acceptable",
            "ipfs://Qm123"
        );

        assertEq(validator.validationCount(REQUEST_HASH), 1);
        assertEq(validator.totalValidations(), 1);

        TrustDeskOpenValidator.ExternalValidation memory v = validator.getValidation(REQUEST_HASH, 0);
        assertEq(v.validator, alice);
        assertEq(v.agentId, AGENT_ID);
        assertEq(v.requestHash, REQUEST_HASH);
        assertTrue(v.approved);
        assertEq(v.reason, "Looks good, risk is acceptable");
        assertEq(v.evidenceURI, "ipfs://Qm123");
    }

    function test_validateTrade_emitsEvent() public {
        vm.expectEmit(true, true, true, true);
        emit TrustDeskOpenValidator.TradeValidated(
            alice,
            AGENT_ID,
            REQUEST_HASH,
            false,
            "Too risky",
            ""
        );

        vm.prank(alice);
        validator.validateTrade(AGENT_ID, REQUEST_HASH, false, "Too risky", "");
    }

    function test_validateTrade_forwardsToRegistry() public {
        vm.prank(alice);
        validator.validateTrade(AGENT_ID, REQUEST_HASH, true, "LGTM", "https://evidence.example");

        assertEq(mockRegistry.callCount(), 1);

        (
            bytes32 reqHash,
            bool approved,
            string memory responseURI,
            ,
            string memory tags
        ) = mockRegistry.calls(0);

        assertEq(reqHash, REQUEST_HASH);
        assertTrue(approved);
        assertEq(responseURI, "https://evidence.example");
        assertEq(tags, "trade,external,trustdesk");
    }

    function test_multipleValidators() public {
        vm.prank(alice);
        validator.validateTrade(AGENT_ID, REQUEST_HASH, true, "Approve", "");

        vm.prank(bob);
        validator.validateTrade(AGENT_ID, REQUEST_HASH, false, "Reject", "ipfs://Qm456");

        assertEq(validator.validationCount(REQUEST_HASH), 2);
        assertEq(validator.totalValidations(), 2);

        TrustDeskOpenValidator.ExternalValidation memory v0 = validator.getValidation(REQUEST_HASH, 0);
        TrustDeskOpenValidator.ExternalValidation memory v1 = validator.getValidation(REQUEST_HASH, 1);

        assertEq(v0.validator, alice);
        assertTrue(v0.approved);

        assertEq(v1.validator, bob);
        assertFalse(v1.approved);
    }

    // ---- Revert cases ----

    function test_revert_zeroRequestHash() public {
        vm.expectRevert(TrustDeskOpenValidator.ZeroRequestHash.selector);
        validator.validateTrade(AGENT_ID, bytes32(0), true, "reason", "");
    }

    function test_revert_emptyReason() public {
        vm.expectRevert(TrustDeskOpenValidator.EmptyReason.selector);
        validator.validateTrade(AGENT_ID, REQUEST_HASH, true, "", "");
    }

    // ---- Immutable state ----

    function test_registryIsImmutable() public view {
        assertEq(address(validator.registry()), address(mockRegistry));
    }
}
