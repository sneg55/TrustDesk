// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console2} from "forge-std/Script.sol";
import {MockValidationRegistry} from "../src/MockValidationRegistry.sol";
import {TrustDeskOpenValidator} from "../src/TrustDeskOpenValidator.sol";

/// @notice Deploy MockValidationRegistry + TrustDeskOpenValidator to Base Sepolia.
contract DeployAll is Script {
    function run() external {
        vm.startBroadcast();

        // 1. Deploy mock registry
        MockValidationRegistry registry = new MockValidationRegistry();
        console2.log("MockValidationRegistry:", address(registry));

        // 2. Deploy open validator pointing at the registry
        TrustDeskOpenValidator validator = new TrustDeskOpenValidator(address(registry));
        console2.log("TrustDeskOpenValidator:", address(validator));

        vm.stopBroadcast();
    }
}
