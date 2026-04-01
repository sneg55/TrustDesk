# Contracts Implementation Plan (TrustDeskOpenValidator)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the default Foundry scaffold with TrustDeskOpenValidator — an open validation contract that lets anyone post assessments of TrustDesk trades via ERC-8004.

**Architecture:** Single Solidity contract wrapping the ERC-8004 Validation Registry. Permissionless — any wallet can validate any trade. Events emitted for dashboard consumption.

**Tech Stack:** Solidity 0.8.24, Foundry (forge), Base Sepolia

---

## Task 1: IValidationRegistry Interface and foundry.toml Update

**Files:**
- `contracts/src/interfaces/IValidationRegistry.sol` (create)
- `contracts/foundry.toml` (edit)

### 1a. Create `contracts/src/interfaces/IValidationRegistry.sol`

```solidity
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
```

### 1b. Update `contracts/foundry.toml`

Ensure the profile targets Solidity 0.8.24 and Base Sepolia:

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc_version = "0.8.24"
evm_version = "cancun"

[rpc_endpoints]
base_sepolia = "${BASE_SEPOLIA_RPC_URL}"

[etherscan]
base_sepolia = { key = "${BASESCAN_API_KEY}", url = "https://api-sepolia.basescan.org/api" }
```

### Verification

```bash
cd contracts && forge build
```

Expect: successful compilation with no sources yet importing the interface (just a clean build).

---

## Task 2: TrustDeskOpenValidator Contract

**Files:**
- `contracts/src/TrustDeskOpenValidator.sol` (create)
- `contracts/src/Counter.sol` (delete)

### 2a. Delete the scaffold

Remove `contracts/src/Counter.sol` and `contracts/test/Counter.t.sol` (the default Foundry template files).

### 2b. Create `contracts/src/TrustDeskOpenValidator.sol`

```solidity
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
```

### Verification

```bash
cd contracts && forge build
```

Expect: clean compilation, no warnings.

---

## Task 3: Tests

**Files:**
- `contracts/test/TrustDeskOpenValidator.t.sol` (create)

### 3a. Create `contracts/test/TrustDeskOpenValidator.t.sol`

```solidity
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
```

### Verification

```bash
cd contracts && forge test -vvv
```

Expect: all 7 tests pass.

---

## Task 4: Deploy Script

**Files:**
- `contracts/script/Deploy.s.sol` (create)
- `contracts/script/Counter.s.sol` (delete, if present)

### 4a. Delete the scaffold deploy script

Remove `contracts/script/Counter.s.sol` if it exists.

### 4b. Create `contracts/script/Deploy.s.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {TrustDeskOpenValidator} from "../src/TrustDeskOpenValidator.sol";

/// @notice Deploy TrustDeskOpenValidator to Base Sepolia.
/// @dev Usage:
///   VALIDATION_REGISTRY=0x... forge script script/Deploy.s.sol \
///     --rpc-url base_sepolia --broadcast --verify
contract DeployTrustDeskOpenValidator is Script {
    function run() external {
        address registryAddr = vm.envAddress("VALIDATION_REGISTRY");

        vm.startBroadcast();
        TrustDeskOpenValidator validator = new TrustDeskOpenValidator(registryAddr);
        vm.stopBroadcast();

        console2.log("TrustDeskOpenValidator deployed at:", address(validator));
        console2.log("Registry:", registryAddr);
    }
}
```

### Verification

```bash
cd contracts && forge build
```

Expect: script compiles cleanly. Actual deployment is a manual step using:

```bash
cd contracts
VALIDATION_REGISTRY=0x<registry_address> forge script script/Deploy.s.sol \
  --rpc-url base_sepolia \
  --broadcast \
  --verify
```

---

## Summary

| Task | Description | Files | Verification |
|------|-------------|-------|--------------|
| 1 | IValidationRegistry interface + foundry.toml | `contracts/src/interfaces/IValidationRegistry.sol`, `contracts/foundry.toml` | `forge build` |
| 2 | TrustDeskOpenValidator contract (replace Counter.sol) | `contracts/src/TrustDeskOpenValidator.sol` | `forge build` |
| 3 | Full test suite with mock registry | `contracts/test/TrustDeskOpenValidator.t.sol` | `forge test -vvv` |
| 4 | Deploy script for Base Sepolia | `contracts/script/Deploy.s.sol` | `forge build` |
