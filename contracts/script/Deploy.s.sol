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
